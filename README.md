# Multi-Agent AI Coding Assistant

A self-correcting coding system where AI agents collaborate to produce working code. The **Clarifier** refines requirements, the **Coder** implements them, the **Tester** validates functionality, and the system **auto-recovers** from failures.

## Overview

This system demonstrates multi-agent collaboration using the [AG2 framework](https://docs.ag2.ai/). It uses:

- **Clarifier Agent**: Asks clarifying questions to understand requirements better (optional)
- **Coder Agent**: Produces complete, runnable code based on the task
- **Tester Agent**: Generates pytest tests for the code
- **Runner**: Runs tests and provides feedback for self-correction

The system iteratively improves code by passing test failure details back to the Coder until tests pass or max rounds reached.

## Architecture

```
User Task → Clarifier (optional) → Technical Questions → Coder → Code
                                                       ↓
                                                  Tester → Tests
                                                       ↓
                                                  Runner → Results
                                                       ↓
                                    Fix needed? →→ Coder → Tests (repeat)
                                         ↓ (passed/approved)
                                         DONE
```

## Supported Languages

- Python (default)
- JavaScript
- TypeScript
- Java
- C++
- Go
- Rust

## Installation

```bash
pip install -r requirements.txt
```

Configure your OpenRouter API endpoint in `.env`:

```
OPENROUTER_BASE_URL=https://your-api-endpoint.com/v1
OPENROUTER_API_KEY=your-api-key
OPENROUTER_MODEL=your-model
```

## Usage

### Command-Line Options

```bash
python coder_framework.py [OPTIONS]

Options:
  --task, -t TEXT       Task description (required)
  --language, -l STR   Target language (default: python)
  --max-rounds, -r INT Max iterations (default: 10)
  --output, -o FILE    Output filename
  --no-clarify        Skip clarifying questions
  --answers           PreProvide answers to clarification questions
  --clear, -c         Clear output folder before running
```

### Examples

```bash
# Simple function
python coder_framework.py -t "return hello world"

# Stack implementation with max 3 rounds
python coder_framework.py -t "implement a stack" -r 3

# Without clarification
python coder_framework.py -t "implement a queue" --no-clarify

# PreProvide answers
python coder_framework.py -t "implement a stack" -l python --answers LIFO push pop peek
```

### Interactive Mode

After code generation, you'll be prompted:

- **(m)ake changes**: Add modifications to the task and regenerate
- **(n)ew task**: Clear and start a new task
- **(q)uit**: Exit

## Output Files

- `output_code/solution.py` - Generated code
- `output_code/test_code.py` - Generated tests
- `output_code/iteration_N.py` - Code snapshots per round
- `output_code/conversation.log` - Session log

## Design Decisions

### Three-Agent Pattern with Self-Correction

1. **Clarifier**: Ensures clear requirements through questions (optional)
2. **Coder**: Produces complete, production-ready code
3. **Tester**: Generates comprehensive pytest tests
4. **Runner**: Executes tests and reports results

### Self-Correction Loop

- Test failures are captured with context (test name, assertion details)
- Last 3 failures passed to next round's Coder
- Coder receives both the error and the previous code to fix
- Tests regenerate after each code change

### Test File Handling

- Output file named `solution.py` (avoids stdlib conflicts)
- Tests import from `solution` module (e.g., `from solution import MyClass`)
- Tests run in output directory with `pytest -v`
- Exit code 0 = pass, non-zero = fail

### Iteration Tracking

- Each round saves code to `iteration_N.py`
- Session log captures round-by-round results
- `outer_failure_history` tracks failures across manual "m" attempts

### Termination

- Tests pass: status shows APPROVED
- Tests fail after max rounds: status shows NOT APPROVED
- User can continue with "m" to make changes

### Model Configuration

- **Default Model**: `openai/gpt-4.1-mini` (via OpenRouter)
- **API**: OpenRouter-compatible endpoint via .env

## File Structure

```
ai-agent-coder/
├── coder_framework.py    # Main implementation (~675 lines)
├── requirements.txt     # Python dependencies
├── .env                 # API configuration
├── .gitignore           # Git ignore rules
├── README.md            # This file
└── output_code/        # Generated code/logs
    ├── solution.py       # Final code
    ├── test_code.py     # Test code
    ├── iteration_N.py  # Round snapshots
    └── conversation.log
```

## Workflow Example

1. User runs: `python coder_framework.py -t "implement a stack" -r 3`
2. Clarifier asks questions (unless `--no-clarify`)
3. Coder generates Stack class
4. Tester generates pytest tests (push, pop, peek, is_empty, size)
5. Runner executes pytest
   - If fail: failure details → Coder for fix attempt
   - If pass: show APPROVED status
6. Repeat up to max rounds
7. Show final code and status

## Key Features

- **Auto-fix**: Test failures fed back to Coder with context
- **Test reuse**: On "make changes", existing tests reused (faster)
- **Failure history**: Last 3 failures tracked across iterations
- **Class support**: Tests correctly import classes, not just functions
- **Terminal UI**: Color-coded output (green=pass, red=fail, blue=info)
- **Iteration files**: Snapshots saved per round for reference