import os
import sys
import subprocess
import argparse
import re
import json
from typing import Optional, List, Tuple
from dotenv import load_dotenv

import autogen
from autogen import ConversableAgent

load_dotenv()

OUTPUT_DIR = "output_code"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CODE_FILE = "code.py"
TEST_FILE = "test_code.py"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CODE_TEMPLATES = {
    "python": {"extension": ".py"},
    "javascript": {"extension": ".js"},
    "typescript": {"extension": ".ts"},
    "java": {"extension": ".java"},
    "cpp": {"extension": ".cpp"},
    "go": {"extension": ".go"},
    "rust": {"extension": ".rs"},
}


# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------

def get_llm_config() -> dict:
    """Load LLM configuration from environment variables."""
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPENROUTER_API_KEY", "dummy")
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini")
    return {
        "config_list": [
            {
                "model": model,
                "base_url": base_url,
                "api_type": "openai",
                "api_key": api_key,
            }
        ],
        "cache_seed": None,
    }


def extract_code_block(content: str, language: str = "python", func_name: str = None) -> str:
    if not content:
        return ""

    block_pattern = r"```(?:\w*)\s*\n?(.*?)```"
    blocks = re.findall(block_pattern, content, re.DOTALL)

    if blocks:
        scored = []
        for code in blocks:
            code = code.strip()
            s = len(code) // 50
            if language.lower() in content.split(code)[0][-200:].lower():
                s += 10
            if func_name and f"def {func_name}" in code:
                s += 20
            scored.append((s, code))
        scored.sort(reverse=True, key=lambda x: x[0])
        best_code = scored[0][1]
        if best_code:
            return best_code

    if "def " in content or "class " in content or "fn " in content:
        return content.strip()
    return ""


def get_last_agent_message(chat_result, agent_name: str) -> str:
    for msg in reversed(chat_result.chat_history):
        if msg.get("name") == agent_name:
            return msg.get("content", "")
    return ""


def run_tests(test_file: str) -> Tuple[bool, List[str], str]:
    """Run the test file from its own directory so 'code' imports correctly."""
    try:
        test_dir = os.path.dirname(test_file)
        test_name = os.path.basename(test_file)
        result = subprocess.run(
            [sys.executable, test_name],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=test_dir,
        )
        combined_output = result.stdout + result.stderr
        failed_lines = [
            line.strip()
            for line in combined_output.split('\n')
            if 'FAILED' in line or 'AssertionError' in line or 'ERROR' in line
        ]
        passed = result.returncode == 0 and not failed_lines
        return passed, failed_lines[:5], combined_output
    except Exception as e:
        return False, [str(e)], ""


def create_responder() -> ConversableAgent:
    return ConversableAgent(
        name="Responder",
        llm_config=get_llm_config(),
        system_message="You are a helpful assistant.",
        human_input_mode="NEVER",
    )


# ----------------------------------------------------------------------
# Clarifier (optional)
# ----------------------------------------------------------------------

def ask_clarifying_questions(task: str, language: str, user_answers: List[str] = None) -> str:
    # Generate questions using a direct LLM call
    clarifier = ConversableAgent(
        name="Clarifier",
        llm_config=get_llm_config(),
        system_message=(
            "You are a coding-task clarifier. Generate 2-4 clarifying questions about the task. "
            "Reply ONLY with a JSON array of strings. Example: [\"question 1\", \"question 2\"]"
        ),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
    )

    responder = create_responder()
    chat_result = clarifier.initiate_chat(
        recipient=responder,
        message=f"Generate clarifying questions for: {task}",
        max_turns=1,
    )

    content = get_last_agent_message(chat_result, "Responder")
    questions = []
    
    # Try to parse JSON
    match = re.search(r"\[.*\]", content, re.DOTALL) if content else None
    if match:
        try:
            questions = json.loads(match.group(0))
            if isinstance(questions, list):
                questions = [q for q in questions if isinstance(q, str)]
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Fallback: extract lines ending with ?
    if not questions:
        questions = [l.strip() for l in content.split('\n') if '?' in l][:4]

    if not questions:
        print("\n⚠ No clarifying questions generated - proceeding without clarification.\n")
        return task

    print("\n=== Clarifying Questions ===")
    # Clean questions - remove existing numbering prefixes
    cleaned = []
    for q in questions:
        q = re.sub(r"^\d+\.?\s*", "", q).strip()
        if q:
            cleaned.append(q)
    for i, q in enumerate(cleaned, 1):
        print(f"{i}. {q}")

    # NOW ask the USER for answers
    answers = []
    if user_answers is not None:
        answers = user_answers[:len(questions)]
        print(f"\nUsing provided answers: {answers}")
    else:
        # Interactive input from USER
        print("\nYour answers (press Enter to skip, or answer each question):")
        try:
            for i, q in enumerate(questions, 1):
                try:
                    ans = input(f"  Q{i}: ").strip()
                    if ans:
                        answers.append(ans)
                except EOFError:
                    break
        except (EOFError, OSError) as e:
            print(f"  (Input error: {e} - skipping)")
        print()

    if not answers:
        print("(Proceeding without additional clarifications)\n")
        return task

    enriched = task + "\n\n=== Requirements from User ===\n" + "\n".join(f"- {a}" for a in answers)
    return enriched


# ----------------------------------------------------------------------
# Main coding session with iterative feedback
# ----------------------------------------------------------------------

class CodeManager:
    def __init__(self):
        self.code = ""
        self.history = []

    def set_code(self, code: str):
        self.code = code
        self.history.append(code)

    def get_code(self) -> str:
        return self.code

    def save(self, filepath: str, code: str):
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write(code)


def run_coding_session(
    task: str,
    language: str = "python",
    max_rounds: int = 10,
    output_file: str = "",
    ask_clarify: bool = True,
    clarify_answers: List[str] = None,
) -> Tuple[str, bool, str]:
    if language not in CODE_TEMPLATES:
        print(f"Warning: unsupported language '{language}', falling back to Python.")
        language = "python"

    code_manager = CodeManager()
    log_entries = []

    task_with_clarifications = task
    if ask_clarify:
        task_with_clarifications = ask_clarifying_questions(task, language, clarify_answers)
        log_entries.append(f"Clarified task: {task_with_clarifications[:100]}...")

    output_file = output_file or CODE_FILE
    filepath = os.path.join(OUTPUT_DIR, output_file)
    test_filepath = os.path.join(OUTPUT_DIR, TEST_FILE)

    print(f"\n=== 3‑Agent Coder (with feedback) ===")
    print(f"Task: {task_with_clarifications.split(chr(10))[0]}...")
    print(f"Language: {language}")
    print(f"Max rounds: {max_rounds}\n")

    round_num = 1
    approved = False
    last_code = ""
    last_error = ""

    while round_num <= max_rounds and not approved:
        print(f"--- Round {round_num} ---")

        # ------------------- Coder -------------------
        print("[1/3] Coder...")
        coder = ConversableAgent(
            name="Coder",
            llm_config=get_llm_config(),
            system_message=(
                "You are a skilled programmer. Write complete, well‑structured code. "
                "Output ONLY the code inside a single fenced code block."
            ),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )

        if round_num == 1:
            prompt = f"Write complete code for:\n{task_with_clarifications}\n\nLanguage: {language}"
        else:
            prompt = (
                f"The previous code failed tests. Please fix it.\n"
                f"ORIGINAL TASK:\n{task_with_clarifications}\n\n"
                f"YOUR LAST CODE:\n```{language}\n{last_code}\n```\n\n"
                f"TEST FAILURE DETAILS:\n{last_error[:1000]}\n\n"
                f"Output only the corrected code."
            )

        responder = create_responder()
        chat_result = coder.initiate_chat(recipient=responder, message=prompt, max_turns=1)
        content = get_last_agent_message(chat_result, "Responder")
        new_code = extract_code_block(content, language)

        if not new_code or len(new_code) < 10:
            print("  ERROR: Could not extract valid code.")
            print(f"  Raw content (first 300 chars): {content[:300]}")
            log_entries.append(f"[Round {round_num}] Coder: extraction failed")
            round_num += 1
            continue

        code_manager.save(filepath, new_code)
        code_manager.set_code(new_code)
        last_code = new_code
        print(f"  Code: {len(new_code)} chars")
        log_entries.append(f"[Round {round_num}] Coder: {len(new_code)} chars")

        # ------------------- Test Generator -------------------
        print("[2/3] TestGen...")
        func_matches = re.findall(r'def (\w+)\s*\(', new_code)
        func_name = "THE_FUNCTION"
        for name in func_matches:
            if not name.startswith("_") and name != "__init__":
                func_name = name
                break
        if func_name == "THE_FUNCTION" and func_matches:
            func_name = func_matches[0]

        test_gen = ConversableAgent(
            name="TestGen",
            llm_config=get_llm_config(),
            system_message=(
                "You are a test engineer. Write comprehensive unit tests using pytest. "
                "Output ONLY the test code inside a single fenced code block. "
                "Do not include the implementation under test."
            ),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )

        test_prompt = (
            f"Write tests for the following {language} code:\n```{language}\n{new_code}\n```\n\n"
            f"IMPORTANT: Write ONLY test functions that call {func_name}(). "
            f"Import the implementation if necessary. Output only the test code."
        )

        chat_result = test_gen.initiate_chat(recipient=create_responder(), message=test_prompt, max_turns=1)
        content = get_last_agent_message(chat_result, "Responder")
        test_code = extract_code_block(content, language)

        if not test_code or len(test_code) < 10:
            print("  WARNING: No valid test code generated.")
            log_entries.append(f"[Round {round_num}] TestGen: failed")
            last_error = "No tests available."
            round_num += 1
            continue

        # Fix placeholder module names like 'your_module' -> 'code'
        test_code = re.sub(
            r'\b(your_module|solution|implementation|main|app|my_module)\b',
            'code',
            test_code,
            flags=re.IGNORECASE
        )

        code_manager.save(test_filepath, test_code)
        print(f"  Tests: {len(test_code)} chars")
        log_entries.append(f"[Round {round_num}] TestGen: {len(test_code)} chars")

        # ------------------- Runner -------------------
        print("[3/3] Runner...")
        passed, failed_lines, full_output = run_tests(test_filepath)
        if passed:
            approved = True
            print("  ✓ ALL TESTS PASSED")
            log_entries.append(f"[Round {round_num}] Runner: PASSED")
        else:
            error_text = failed_lines[0][:200] if failed_lines else "Unknown failure"
            last_error = f"FAILED: {error_text}\n\nFull run output:\n{full_output[:500]}"
            print(f"  ✗ FAILED: {error_text}")
            log_entries.append(f"[Round {round_num}] Runner: FAILED - {error_text[:80]}...")

        round_num += 1

    final_code = code_manager.get_code()
    code_manager.save(filepath, final_code)

    print(f"\n=== Session Complete ===")
    print(f"Output: {filepath}")
    print(f"Code length: {len(final_code)} chars")
    print(f"Rounds run: {round_num - 1}")
    print(f"Approved: {approved}")

    log_entries.insert(0, "=== Coding Session Log ===")
    log_entries.insert(1, f"Task: {task_with_clarifications}")
    log_entries.append(f"Final rounds: {round_num - 1}")
    log_entries.append(f"Approved: {approved}")

    log_filepath = os.path.join(OUTPUT_DIR, "conversation.log")
    with open(log_filepath, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(log_entries))

    return final_code, approved, filepath


# ----------------------------------------------------------------------
# CLI entry point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Self‑fixing multi‑agent coder")
        parser.add_argument("--task", "-t", type=str, required=True)
        parser.add_argument("--language", "-l", type=str, default="python")
        parser.add_argument("--max-rounds", "-r", type=int, default=10)
        parser.add_argument("--output", "-o", type=str, default=None)
        parser.add_argument("--no-clarify", action="store_true")
        parser.add_argument("--answers", nargs="*")

        args = parser.parse_args()

        final_code, approved, path = run_coding_session(
            task=args.task,
            language=args.language,
            max_rounds=args.max_rounds,
            output_file=args.output or "",
            ask_clarify=not args.no_clarify,
            clarify_answers=args.answers if args.answers else None,
        )

        print("\n--- Generated Code Preview ---")
        print(final_code[:500] if final_code else "No code produced.")
    except Exception as e:
        print("\nFATAL ERROR:")
        import traceback
        traceback.print_exc()
        sys.exit(1)