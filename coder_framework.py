import os
import sys
import subprocess
import argparse
import re
import json
import shutil
from typing import Optional, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

import autogen
from autogen import ConversableAgent

load_dotenv()

OUTPUT_DIR = "output_code"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CODE_FILE = "solution.py"
TEST_FILE = "test_code.py"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ----------------------------------------------------------------------
# Terminal UI - Colors and formatting
# ----------------------------------------------------------------------

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'
    DIM = '\033[2m'
    
    @classmethod
    def strip(cls, s: str) -> str:
        return (s.replace(cls.HEADER, '').replace(cls.BLUE, '')
                 .replace(cls.GREEN, '').replace(cls.YELLOW, '')
                 .replace(cls.RED, '').replace(cls.BOLD, '')
                 .replace(cls.ENDC, '').replace(cls.DIM, ''))


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def header(title: str, width: int = 60):
    """Print a formatted header."""
    print()
    print(f"{Colors.HEADER}{Colors.BOLD}═{title:^{width}}{Colors.ENDC}")
    print(f"{Colors.DIM}─{'─' * width}{Colors.ENDC}")


def step_label(step_num: int, total: int, label: str):
    """Print step indicator."""
    pct = step_num / total * 100
    bar_len = int(pct / 5)
    bar = '█' * bar_len + '░' * (20 - bar_len)
    color = Colors.GREEN if pct == 100 else Colors.YELLOW if pct > 50 else Colors.BLUE
    print(f"{color}[{bar}] {step_num}/{total} {label}{Colors.ENDC}")


def success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")


def error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.ENDC}")


def info(msg: str):
    print(f"{Colors.BLUE}▸ {msg}{Colors.ENDC}")


def code_preview(code: str, lines: int = 15) -> str:
    """Get a preview of code for display."""
    code_lines = code.strip().split('\n')
    if len(code_lines) <= lines:
        return code.strip()
    return '\n'.join(code_lines[:lines]) + f"\n  ... ({len(code_lines) - lines} more lines)"


def diff_summary(old: str, new: str) -> str:
    """Show what changed between old and new code."""
    old_lines = set(old.split('\n'))
    new_lines = set(new.split('\n'))
    added = new_lines - old_lines
    removed = old_lines - new_lines
    return f"+{len(added)} -{len(removed)} lines"


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

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
    """Run the test file with pytest from its own directory so 'code' imports correctly."""
    try:
        test_dir = os.path.dirname(test_file)
        test_name = os.path.basename(test_file)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_name, "-v"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=test_dir,
        )
        combined_output = result.stdout + result.stderr
        
        failed_lines = []
        lines = combined_output.split('\n')
        
        test_count = 0
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            if 'error collecting test' in line_lower or 'importerror' in line_lower or 'modulenotfounderror' in line_lower:
                failed_lines.append(f"Import error: {line.strip()[:100]}")
                continue
            
            if 'collected' in line_lower and 'items' in line_lower:
                test_count = int(''.join(filter(str.isdigit, line.split('items')[0])))
                continue
            
            if 'short test summary info' in line_lower:
                continue
            
            if line.strip().startswith('test_') and '::' in line:
                if 'failed' in line_lower:
                    failed_lines.append(f"  {line.strip()[:120]}")
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('AssertionError'):
                        failed_lines[-1] += f" | {lines[i + 1].strip()[:80]}"
                continue
            
            if line.strip().startswith('failed') and '::' in line_lower:
                failed_lines.append(f"  {line.strip()[:150]}")
                continue
        
        passed = False
        if result.returncode == 0 and test_count > 0:
            passed = True
        elif result.returncode != 0:
            passed = False
        elif test_count == 0:
            failed_lines.insert(0, f"No tests collected")
        
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
        self.test_history = []

    def set_code(self, code: str):
        self.code = code
        self.history.append({
            'code': code,
            'timestamp': datetime.now().isoformat()
        })

    def get_code(self) -> str:
        return self.code

    def save(self, filepath: str, code: str):
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write(code)

    def save_iteration(self, output_dir: str, round_num: int, language: str = "python"):
        """Save code as iteration file."""
        ext = CODE_TEMPLATES.get(language, {}).get("extension", ".py")
        filepath = os.path.join(output_dir, f"iteration_{round_num}{ext}")
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write(self.code)
        return filepath


def run_coding_session(
    task: str,
    language: str = "python",
    max_rounds: int = 10,
    output_file: str = "",
    ask_clarify: bool = True,
    clarify_answers: List[str] = None,
    reuse_tests: bool = False,
    existing_test_file: str = None,
    previous_error: str = None,
) -> Tuple[str, bool, str]:
    if language not in CODE_TEMPLATES:
        print(f"Warning: unsupported language '{language}', falling back to Python.")
        language = "python"

    code_manager = CodeManager()
    log_entries = []
    failure_history = []
    MAX_FAILURES = 3

    task_with_clarifications = task
    if ask_clarify:
        task_with_clarifications = ask_clarifying_questions(task, language, clarify_answers)
        log_entries.append(f"Clarified task: {task_with_clarifications[:100]}...")

    output_file = output_file or CODE_FILE
    filepath = os.path.join(OUTPUT_DIR, output_file)
    test_filepath = os.path.join(OUTPUT_DIR, TEST_FILE)

    print(f"\n=== 3‑Agent Coder (with feedback) ===")
    info(f"Task: {task_with_clarifications.split(chr(10))[0]}...")
    info(f"Language: {language}")
    info(f"Max rounds: {max_rounds}")
    print()

    round_num = 1
    approved = False
    while round_num <= max_rounds and not approved:
        print(f"--- Round {round_num} ---")

        # ------------------- Coder -------------------
        info("[1/3] Generating code...")
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
            if previous_error:
                prompt += (
                    f"\n\nIMPORTANT: The previous implementation had failing tests:\n"
                    f"{previous_error[:1000]}\n\n"
                    f"Fix these issues while keeping working functionality."
                )
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
        info("[2/3] Generating tests...")
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
            f"IMPORTANT: Write test functions that verify the implementation works correctly. "
            f"If it's a class, import it and create instances with the constructor. "
            f"If it's a function, import and call it. "
            f"Examples: 'from solution import MyClass' or 'from solution import my_func'. "
            f"Output only the test code."
        )

        # Skip test generation if reusing existing tests
        if reuse_tests and existing_test_file and os.path.exists(existing_test_file):
            info("[2/3] Reusing existing tests...")
            with open(existing_test_file, "r", encoding="utf-8", errors="replace") as f:
                test_code = f.read()
            log_entries.append(f"[Round {round_num}] TestGen: reused {len(test_code)} chars")
        else:
            chat_result = test_gen.initiate_chat(recipient=create_responder(), message=test_prompt, max_turns=1)
            content = get_last_agent_message(chat_result, "Responder")
            test_code = extract_code_block(content, language)

            if not test_code or len(test_code) < 10:
                print("  WARNING: No valid test code generated.")
                log_entries.append(f"[Round {round_num}] TestGen: failed")
                last_error = "No tests available."
                round_num += 1
                continue

        # Fix placeholder module names like 'your_module' -> 'solution'
        test_code = re.sub(
            r'\b(your_module|solution|implementation|app|my_module)\b',
            'solution',
            test_code,
            flags=re.IGNORECASE
        )

        # Save test file
        code_manager.save(test_filepath, test_code)

        code_manager.save(test_filepath, test_code)
        print(f"  Tests: {len(test_code)} chars")
        log_entries.append(f"[Round {round_num}] TestGen: {len(test_code)} chars")

        # ------------------- Runner -------------------
        print("[3/3] Runner...")
        passed, failed_lines, full_output = run_tests(test_filepath)
        if passed:
            approved = True
            success("ALL TESTS PASSED")
            log_entries.append(f"[Round {round_num}] Runner: PASSED")
        else:
            error_text = failed_lines[0][:200] if failed_lines else "Unknown failure"
            last_error = f"FAILED: {error_text}\n\nFull run output:\n{full_output[:500]}"
            error(f"{error_text}")
            log_entries.append(f"[Round {round_num}] Runner: FAILED - {error_text[:80]}...")
            
            if len(failure_history) >= MAX_FAILURES:
                failure_history.pop(0)
            failure_history.append(error_text[:500])

        # Track failures for next round
        context_error = "\n".join(failure_history) if failure_history else None

        # Save iteration AFTER code generation (before tests)
        code_manager.save_iteration(OUTPUT_DIR, round_num, language)

        round_num += 1

    # Save final code
    final_code = code_manager.get_code()
    code_manager.save(filepath, final_code)

    # Session summary
    print()
    header("SESSION COMPLETE", 50)
    info(f"Output: {filepath}")
    info(f"Rounds: {round_num - 1}")
    info(f"Code: {len(final_code)} chars")
    success(f"Status: {'APPROVED' if approved else 'NOT APPROVED'}")

    # Save log
    log_entries.insert(0, "=== Coding Session Log ===")
    log_entries.insert(1, f"Task: {task_with_clarifications}")
    log_entries.append(f"Final rounds: {round_num - 1}")
    log_entries.append(f"Approved: {approved}")

    log_filepath = os.path.join(OUTPUT_DIR, "conversation.log")
    with open(log_filepath, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(log_entries))

    return final_code, approved, filepath, last_error if not approved else None


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
        parser.add_argument("--clear", action="store_true", help="Clear output folder")

        args = parser.parse_args()

        # Clear output folder if requested (or when starting new session)
        def clear_output():
            if os.path.exists(OUTPUT_DIR):
                for f in os.listdir(OUTPUT_DIR):
                    path = os.path.join(OUTPUT_DIR, f)
                    if os.path.isfile(path):
                        os.remove(path)
            info("Output folder cleared")

        if args.clear:
            clear_output()

        run_count = 0
        current_test_file = None
        outer_failure_history = []
        
        while True:
            # Skip clarification on repeat runs (user chose 'm')
            skip_clarify = run_count > 0
            
            # Reuse existing test file on subsequent runs
            reuse_tests = run_count > 0 and current_test_file is not None
            
            # Build previous error context for Coder
            context_error = "\n".join(outer_failure_history[-3:]) if outer_failure_history else None
            
            final_code, approved, path, session_error = run_coding_session(
                task=args.task,
                language=args.language,
                max_rounds=args.max_rounds,
                output_file=args.output or "",
                ask_clarify=not skip_clarify and not args.no_clarify,
                clarify_answers=args.answers if args.answers else None,
                reuse_tests=reuse_tests,
                existing_test_file=current_test_file,
                previous_error=context_error,
            )

            filepath = path
            
            # Track failures across outer loop iterations
            if session_error:
                if len(outer_failure_history) >= 3:
                    outer_failure_history.pop(0)
                outer_failure_history.append(session_error[:500])
            
            # Track test file for reuse
            test_path = os.path.join(OUTPUT_DIR, TEST_FILE)
            if os.path.exists(test_path):
                current_test_file = test_path
                
            run_count += 1

            # Show code
            print()
            header("CODE PREVIEW", 50)
            print(code_preview(final_code, 15))

            # Ask user what to do
            print()
            if approved:
                success("All tests passed!")
            else:
                error("Some tests failed")

            # Ask to continue
            print()
            try:
                choice = input(f"{Colors.YELLOW}Make changes (m) / New task (n) / Quit (q)? {Colors.ENDC}").strip().lower()
            except (EOFError, OSError):
                break

            if choice == 'q':
                break
            elif choice == 'n':
                try:
                    args.task = input(f"{Colors.CYAN}Enter new task: {Colors.ENDC}").strip()
                    if not args.task:
                        break
                    args.language = input(f"Language [{args.language}]: ").strip() or args.language
                    clear_output()
                    args.output = ""
                    run_count = 0  # Reset for new task
                except (EOFError, OSError):
                    break
            elif choice == 'm':
                # Make changes - first ask what needs to change
                try:
                    change_input = input(f"{Colors.YELLOW}What changes do you want? {Colors.ENDC}").strip()
                    if change_input:
                        # Append changes to task
                        args.task = f"{args.task}\n\nMake these changes: {change_input}"
                    # Clear output for new attempt
                    clear_output()
                except (EOFError, OSError):
                    break
            else:
                continue

    except Exception as e:
        print()
        error("Fatal error")
        import traceback
        traceback.print_exc()
        sys.exit(1)