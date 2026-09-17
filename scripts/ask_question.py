#!/usr/bin/env python3
"""
Simple NotebookLM Question Interface
Based on MCP server implementation - simplified without sessions

Implements hybrid auth approach:
- Persistent browser profile (user_data_dir) for fingerprint consistency
- Manual cookie injection from state.json for session cookies (Playwright bug workaround)
See: https://github.com/microsoft/playwright/issues/36139
"""

import argparse
import sys
import time
import re
import hashlib
from collections import Counter
from pathlib import Path

from patchright.sync_api import sync_playwright

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from config import (
    QUERY_INPUT_SELECTORS,
    RESPONSE_SELECTORS,
    THINKING_SELECTORS,
    QUERY_TIMEOUT_SECONDS,
    is_notebook_url,
)
from browser_utils import BrowserFactory, StealthUtils


# Follow-up reminder (adapted for stateless operation)
# Since we don't have persistent sessions, we encourage comprehensive questions
FOLLOW_UP_REMINDER = (
    "\n\nEXTREMELY IMPORTANT: Is that ALL you need to know? "
    "You can always ask another question! Think about it carefully: "
    "before responding to the user, review their original request and this answer. "
    "If anything is still unclear or missing, ask another comprehensive question "
    "that includes all necessary context (since each question opens a new browser session)."
)


def ask_notebooklm(question: str, notebook_url: str, headless: bool = True) -> str:
    """
    Ask a question to NotebookLM

    Args:
        question: Question to ask
        notebook_url: NotebookLM / Gemini Notebook notebook URL
        headless: Run browser in headless mode

    Returns:
        Answer text from NotebookLM
    """
    auth = AuthManager()

    if not auth.is_authenticated():
        print("⚠️ Not authenticated. Run: python scripts/run.py auth_manager.py setup")
        return None

    print(f"💬 Asking: {question}")
    print(f"📚 Notebook: {notebook_url}")

    playwright = None
    context = None

    try:
        # Start playwright
        playwright = sync_playwright().start()

        # Launch persistent browser context using factory
        context = BrowserFactory.launch_persistent_context(
            playwright,
            headless=headless
        )

        # Navigate to notebook
        page = context.new_page()
        print("  🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded")

        # Wait for NotebookLM / Gemini Notebook
        page.wait_for_url(is_notebook_url, timeout=15000)

        # Clear transient browser caches to avoid loading stale conversation fragments
        try:
            page.evaluate("""() => {
                try { localStorage.clear(); } catch(e) {}
                try { sessionStorage.clear(); } catch(e) {}
            }""")
        except Exception:
            pass

        # Wait for query input
        print("  ⏳ Waiting for query input...")
        query_element = None
        matched_selector = None

        for selector in QUERY_INPUT_SELECTORS:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    if el.is_visible():
                        tag = el.evaluate("el => el.tagName.toLowerCase()")
                        # Reject top title inputs or general search bars
                        if tag == "input":
                            class_name = el.evaluate("el => el.className || ''")
                            input_type = el.evaluate("el => el.getAttribute('type') || ''").lower()
                            if "title" in class_name or input_type not in ["", "text"]:
                                continue
                        query_element = el
                        matched_selector = selector
                        break
                if query_element:
                    print(f"  ✓ Found input: {matched_selector}")
                    break
            except Exception:
                continue

        if not query_element:
            # Fallback waiting for primary selector
            try:
                query_element = page.wait_for_selector(
                    QUERY_INPUT_SELECTORS[0],
                    timeout=10000,
                    state="visible"
                )
                if query_element:
                    matched_selector = QUERY_INPUT_SELECTORS[0]
                    print(f"  ✓ Found input (fallback): {matched_selector}")
            except Exception:
                pass

        if not query_element:
            print("  ❌ Could not find query input")
            return None

        # Snapshot existing response text hashes before submitting
        baseline_hashes = Counter()
        for selector in RESPONSE_SELECTORS:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    text = el.inner_text().strip()
                    if text:
                        h = hashlib.md5(text.encode("utf-8")).hexdigest()
                        baseline_hashes[h] += 1
            except Exception:
                pass

        # Type question using the matched selector
        print("  ⏳ Typing question...")
        StealthUtils.human_type(page, matched_selector, question)

        # Submit
        print("  📤 Submitting...")
        page.keyboard.press("Enter")

        # Small pause
        StealthUtils.random_delay(500, 1500)

        # Wait for response (poll for stable new text)
        print("  ⏳ Waiting for answer...")

        answer = None
        stable_count = 0
        last_candidate = None
        deadline = time.time() + QUERY_TIMEOUT_SECONDS

        while time.time() < deadline:
            # Check if NotebookLM is still thinking
            is_thinking = False
            for selector in THINKING_SELECTORS:
                try:
                    thinking_el = page.query_selector(selector)
                    if thinking_el and thinking_el.is_visible():
                        is_thinking = True
                        break
                except Exception:
                    pass

            if is_thinking:
                time.sleep(1)
                continue

            # Gather current response elements
            candidate_texts = []
            for selector in RESPONSE_SELECTORS:
                try:
                    elements = page.query_selector_all(selector)
                    for el in elements:
                        text = el.inner_text().strip()
                        if text:
                            h = hashlib.md5(text.encode("utf-8")).hexdigest()
                            candidate_texts.append((h, text))
                except Exception:
                    continue

            if candidate_texts:
                current_counts = Counter([h for h, _ in candidate_texts])
                # Find responses with higher occurrence counts than baseline
                new_candidates = [
                    text for h, text in candidate_texts
                    if current_counts[h] > baseline_hashes.get(h, 0)
                ]

                if new_candidates:
                    # Pick the longest new candidate (ensures fully-rendered streaming answer)
                    candidate = max(new_candidates, key=len)
                    if candidate == last_candidate:
                        stable_count += 1
                        if stable_count >= 3:
                            answer = candidate
                            break
                    else:
                        stable_count = 1
                        last_candidate = candidate
                elif not baseline_hashes:
                    # Fresh session with no prior history: inspect latest element
                    latest_text = candidate_texts[-1][1]
                    if latest_text == last_candidate:
                        stable_count += 1
                        if stable_count >= 3:
                            answer = latest_text
                            break
                    else:
                        stable_count = 1
                        last_candidate = latest_text

            time.sleep(1)

        if not answer:
            print("  ❌ Timeout waiting for answer")
            return None

        print("  ✅ Got answer!")
        # Add follow-up reminder to encourage comprehensive agent queries
        return answer + FOLLOW_UP_REMINDER

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Always clean up
        if context:
            try:
                context.close()
            except Exception:
                pass

        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description='Ask NotebookLM / Gemini Notebook a question')

    parser.add_argument('--question', required=True, help='Question to ask')
    parser.add_argument('--notebook-url', help='NotebookLM / Gemini Notebook URL')
    parser.add_argument('--notebook-id', help='Notebook ID from library')
    parser.add_argument('--show-browser', action='store_true', help='Show browser')

    args = parser.parse_args()

    library = NotebookLibrary()
    notebook_url = args.notebook_url
    resolved_notebook_id = None

    if not notebook_url and args.notebook_id:
        notebook = library.get_notebook(args.notebook_id)
        if notebook:
            notebook_url = notebook['url']
            resolved_notebook_id = args.notebook_id
        else:
            print(f"❌ Notebook '{args.notebook_id}' not found")
            return 1

    if not notebook_url:
        # Check for active notebook first
        active = library.get_active_notebook()
        if active:
            notebook_url = active['url']
            resolved_notebook_id = active['id']
            print(f"📚 Using active notebook: {active['name']}")
        else:
            # Show available notebooks
            notebooks = library.list_notebooks()
            if notebooks:
                print("\n📚 Available notebooks:")
                for nb in notebooks:
                    mark = " [ACTIVE]" if nb.get('id') == library.active_notebook_id else ""
                    print(f"  {nb['id']}: {nb['name']}{mark}")
                print("\nSpecify with --notebook-id or set active:")
                print("python scripts/run.py notebook_manager.py activate --id ID")
            else:
                print("❌ No notebooks in library. Add one first:")
                print("python scripts/run.py notebook_manager.py add --url URL --name NAME --description DESC --topics TOPICS")
            return 1
    elif not resolved_notebook_id:
        # If notebook_url was passed directly, check if it matches a known notebook
        for nb in library.list_notebooks():
            if nb.get('url') == notebook_url:
                resolved_notebook_id = nb.get('id')
                break

    # Ask the question
    answer = ask_notebooklm(
        question=args.question,
        notebook_url=notebook_url,
        headless=not args.show_browser
    )

    if answer:
        # Increment use count on success (non-fatal)
        if resolved_notebook_id:
            try:
                library.increment_use_count(resolved_notebook_id)
            except Exception as e:
                print(f"  ⚠️ Could not update use count: {e}")

        print("\n" + "=" * 60)
        print(f"Question: {args.question}")
        print("=" * 60)
        print()
        print(answer)
        print()
        print("=" * 60)
        return 0
    else:
        print("\n❌ Failed to get answer")
        return 1


if __name__ == "__main__":
    sys.exit(main())
