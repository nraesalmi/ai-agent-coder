import os
import sys
import subprocess
import argparse
import re
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


def get_llm_config():
    base_url = os.getenv("OPENROUTER_BASE_URL")
    return {
        "config_list": [
            {
                "model": "openai/gpt-4.1-mini",
                "base_url": base_url,
                "api_type": "openai",
                "api_key": "dummy",
            }
        ],
        "cache_seed": None,
    }


def extract_code_block(content: str) -> str:
    if not content:
        return ""

    pattern = r"```(?:[a-zA-Z]+\n)?(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        return matches[0].strip()

    if "def " in content or "class " in content:
        return content.strip()

    return content.strip()


def run_tests(test_file: str) -> tuple:
    try:
        result = subprocess.run(
            ["python", test_file],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout + result.stderr
        failed = [l.strip() for l in out.split('\n') if 'FAILED' in l or 'AssertionError' in l]

        if result.returncode == 0 and not failed:
            return True, [], out
        return False, failed[:5], out
    except Exception as e:
        return False, [str(e)], ""


def create_dummy():
    return ConversableAgent(
        name="Dummy",
        llm_config=get_llm_config(),
        system_message="You are a dummy agent.",
        human_input_mode="NEVER",
    )


def run_coding_session(task: str, language: str = "python", max_rounds: int = 10, output_file: str = "", ask_clarify: bool = True):
    output_file = output_file or ""

    if language not in CODE_TEMPLATES:
        language = "python"

    code_manager = CodeManager()
    log_entries = []
    task_with_context = task

    # Agent 0: Clarifier - ask user clarifying questions
    if ask_clarify:
        print(f"\n=== Clarifying Task ===")
        print(f"Task: {task}")
        print(f"Language: {language}\n")
        
        clarifier = ConversableAgent(
            name="Clarifier",
            llm_config=get_llm_config(),
            system_message="You help clarify coding tasks. Generate 2-4 specific questions about requirements, edge cases, error handling, or expected behavior.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
        
        try:
            # Generate questions
            result = clarifier.initiate_chat(
                recipient=create_dummy(),
                message=f"Generate clarifying questions for: {task}",
                max_turns=1,
            )
            
            questions = ""
            for m in result.chat_history:
                c = m.get("content", "")
                if c and "?" in c:
                    questions = c
                    break
            if not questions:
                for m in reversed(result.chat_history):
                    c = m.get("content", "")
                    if c and len(c) > 20:
                        questions = c
                        break
            
            if questions:
                print(f"Clarifying questions:")
                print(f"{questions[:500]}\n")
                
                # Get user answers via input
                print("Your answers (or press Enter to skip):")
                user_answers = input("> ")
                
                if user_answers.strip():
                    task_with_context = f"{task}\n\nUser requirements: {user_answers}"
                    print(f"\n(Including your requirements for the Coder)")
                    log_entries.append(f"User requirements: {user_answers[:100]}...")
                else:
                    print(f"\n(Proceeding without additional clarifications)")
                    log_entries.append(f"No clarifications provided")
                
        except Exception as e:
            print(f"  Note: {e}")
    
    filepath = os.path.join(OUTPUT_DIR, output_file or CODE_FILE)
    test_filepath = os.path.join(OUTPUT_DIR, TEST_FILE)

    print(f"\n=== 3-Agent Coder ===")
    print(f"Task: {task}")
    print(f"Language: {language}")
    print(f"Max Rounds: {max_rounds}\n")

    round_num = 1
    approved = False

    while round_num <= max_rounds and not approved:
        print(f"--- Round {round_num} ---")

        # Agent 1: Coder writes code.py
        print(f"[1/3] Coder...")
        coder = ConversableAgent(
            name="Coder",
            llm_config=get_llm_config(),
            system_message="Write code. Output ONLY code in code blocks.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )

        # Use task with user clarifications if available
        coder_task = task_with_context if 'task_with_context' in dir() and task_with_context else task
        
        try:
            result = coder.initiate_chat(
                recipient=create_dummy(),
                message=f"Write complete code for: {coder_task}\n\nLanguage: {language}\nOutput ONLY code:",
                max_turns=1,
            )

            code = ""
            for m in result.chat_history:
                c = m.get("content", "")
                if c and ("def " in c or "class " in c):
                    code = extract_code_block(c)
                    if code:
                        break
            if not code:
                for m in reversed(result.chat_history):
                    c = m.get("content", "")
                    if c and len(c) > 30:
                        code = extract_code_block(c)
                        break

            if code:
                code_manager.save(filepath, code)
                code_manager.set_code(code)
                print(f"  Code: {len(code)} chars")
                log_entries.append(f"[Round {round_num}] Coder: {len(code)} chars")
            else:
                print(f"  ERROR: No code")
                log_entries.append(f"[Round {round_num}] Coder: ERROR")
                round_num += 1
                continue
        except Exception as e:
            print(f"  Error: {e}")
            log_entries.append(f"[Round {round_num}] Coder Error: {e}")
            round_num += 1
            continue

        curr_code = code_manager.get_code()
        if len(curr_code) < 10:
            print(f"  ERROR: Empty code")
            round_num += 1
            continue

        # Agent 2: Test Generator writes test_code.py
        print(f"[2/3] TestGen...")
        test_gen = ConversableAgent(
            name="TestGen",
            llm_config=get_llm_config(),
            system_message="Write tests. Output ONLY test code with asserts.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )

        try:
            # Extract function/method name from code for the prompt
            # Prefer public methods, not private/__init__/dunder methods
            func_matches = re.findall(r'def (\w+)\s*\(', curr_code)
            func_name = "THE_FUNCTION"
            for name in func_matches:
                if not name.startswith("_") and name != "THE_FUNCTION":
                    func_name = name
                    break
            if func_name == "THE_FUNCTION" and func_matches:
                func_name = func_matches[0]
            
            result = test_gen.initiate_chat(
                recipient=create_dummy(),
                message=f"Create tests for this code:\n{curr_code}\n\nIMPORTANT: Write ONLY test functions that call {func_name}(). Do NOT include the {func_name} function definition itself. Output ONLY test code:",
                max_turns=1,
            )

            test_code = ""
            for m in result.chat_history:
                c = m.get("content", "")
                if c and ("assert " in c or "unittest" in c or "pytest" in c):
                    test_code = extract_code_block(c)
                    if test_code:
                        break
            if not test_code:
                for m in reversed(result.chat_history):
                    c = m.get("content", "")
                    if c and len(c) > 30:
                        test_code = extract_code_block(c)
                        break

            if test_code:
                code_manager.save(test_filepath, test_code)
                print(f"  Tests: {len(test_code)} chars")
                log_entries.append(f"[Round {round_num}] TestGen: {len(test_code)} chars")
            else:
                print(f"  WARNING: No tests")
                log_entries.append(f"[Round {round_num}] TestGen: No tests")
        except Exception as e:
            print(f"  Error: {e}")
            log_entries.append(f"[Round {round_num}] TestGen Error: {e}")

        # Agent 3: Run tests
        print(f"[3/3] Runner...")
        if os.path.exists(test_filepath):
            passed, failed, output = run_tests(test_filepath)
            if passed:
                approved = True
                print(f"  ✓ PASSED")
                log_entries.append(f"[Round {round_num}] Runner: PASSED")
            else:
                print(f"  ✗ FAILED")
                # Extract meaningful error info
                error_msg = "Unknown error"
                if output:
                    lines = output.strip().split('\n')
                    for line in lines:
                        if "ModuleNotFoundError" in line:
                            error_msg = f"Missing dependency: {line.split('ModuleNotFoundError')[0].strip()}"
                            break
                        elif "ImportError" in line:
                            error_msg = f"Import error: {line.split('ImportError')[0].strip()}"
                            break
                        elif "SyntaxError" in line:
                            error_msg = f"Syntax error"
                            break
                        elif "Error" in line and "File" in line:
                            error_msg = f"File error in test_code.py"
                            break
                    if error_msg == "Unknown error" and failed:
                        # Show the actual assertion/error
                        error_msg = failed[0][:100] if failed else "Test assertion failed"
                
                log_entries.append(f"[Round {round_num}] Runner: FAILED - {error_msg}")
                print(f"  Error: {error_msg}")
                for f in failed[:2]:
                    print(f"    - {f[:80]}")
        else:
            print(f"  ERROR: No test file")

        round_num += 1

    if not approved:
        print(f"\nMax rounds ({max_rounds}) reached")

    final_code = code_manager.get_code()
    code_manager.save(filepath, final_code)

    print(f"\n=== Complete ===")
    print(f"Output: {filepath}")
    print(f"Code: {len(final_code)} chars")
    print(f"Rounds: {round_num - 1}")
    print(f"Approved: {approved}")

    # Save conversation log
    log_entries.insert(0, f"=== Coding Session ===")
    log_entries.insert(1, f"Task: {task}")
    log_entries.append(f"Rounds: {round_num - 1}")
    log_entries.append(f"Approved: {approved}")

    log_filepath = os.path.join(OUTPUT_DIR, "conversation.log")
    with open(log_filepath, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(log_entries))

    return final_code, approved, filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3-agent coder")
    parser.add_argument("--task", "-t", type=str, required=True)
    parser.add_argument("--language", "-l", type=str, default="python")
    parser.add_argument("--max-rounds", "-r", type=int, default=10)
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--no-clarify", action="store_true", help="Skip clarifying questions")

    args = parser.parse_args()

    code, approved, filepath = run_coding_session(
        task=args.task,
        language=args.language,
        max_rounds=args.max_rounds,
        output_file=args.output or "",
        ask_clarify=not args.no_clarify,
    )

    print(f"\n--- Code ---")
    print(code[:500] if code else "None")