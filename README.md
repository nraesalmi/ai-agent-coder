# Multi-Agent AI Coding Assistant

A collaborative coding system where four AI agents work together to produce professional, thorough code. The **Task Analyzer** refines requirements, the **Coder** implements them, the **Tester** validates functionality, and the **Reviewer** approves the final code.

## Overview

This system demonstrates multi-agent collaboration using the [AG2 framework](https://docs.ag2.ai/). It uses:

- **Task Analyzer Agent**: Transforms user tasks into detailed technical specifications with edge cases, docstrings, type hints
- **Coder Agent**: Produces complete, runnable code based on the refined spec
- **Tester Agent**: Tests functionality and edge cases, reports findings
- **Reviewer Agent**: Reviews test results; if tests pass, outputs `[APPROVED]`

The conversation is orchestrated using AG2's native `initiate_chat` mechanism.

## Architecture

```
User Task → Task Analyzer → Technical Spec → Coder → Code
                                                ↓
                                           Tester
                                                ↓
                                           Reviewer
                                                ↓
                              Fix needed? ←→ Coder → Tester → Reviewer (repeat)
                                    ↓ (none/approved)
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
```

## Usage

### Command-Line Options

```bash
python coder_framework.py [OPTIONS]

Options:
  --task, -t TEXT       Task description (required)
  --language, -l STR   Target language (default: python)
  --max-rounds, -r INT   Max iterations (default: 10)
  --output, -o FILE     Output filename
```

### Examples

```bash
# Python function
python coder_framework.py --task "Write a function to calculate factorial of a number"

# API endpoint
python coder_framework.py -t "Create a REST API endpoint for user authentication" -l python

# JavaScript
python coder_framework.py -t "Create a function to debounce events" -l javascript

# Custom output
python coder_framework.py -t "Sort a list using quicksort" -o mysort.py
```

## Output Files

- `output_code/output.py` - Generated code
- `output_code/conversation.log` - Full conversation transcript

## Design Decisions

### Four-Agent Pattern

1. **Task Analyzer**: Ensures thorough requirements with edge cases, docstrings, validation
2. **Coder**: Produces complete, production-ready code
3. **Tester**: Runs test cases for functionality and edge cases, reports findings
4. **Reviewer**: Reviews test results, approves code if tests pass

### Termination

- Tester runs test cases and reports PASS/FAIL
- Reviewer outputs `[APPROVED]` when tests pass and edge cases are handled
- Loop stops at `--max-rounds` limit or when approved

### Output-Only Mode

The Coder outputs code as messages, not executing or writing files. This is safer for user review before saving.

### Model Configuration

- **Model**: `qwen/qwen3.5-flash-02-23` (fast, capable)
- **API**: OpenRouter-compatible endpoint via .env

## File Structure

```
ai-agent-coder/
├── coder_framework.py    # Main implementation
├── requirements.txt   # Python dependencies
├── .env                # API configuration
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── output_code/       # Generated code/logs
```