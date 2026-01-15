import argparse
import subprocess
import sys
import shutil

def main():
    parser = argparse.ArgumentParser(description="Helper tool to find CSS selectors using Playwright Codegen.")
    parser.add_argument("url", help="The URL to inspect (e.g., https://example.com)")
    args = parser.parse_args()

    # Check if playwright is installed
    if not shutil.which("playwright"):
        print("Error: 'playwright' executable not found. Please install it with 'pip install playwright' and 'playwright install'.")
        sys.exit(1)

    print("=" * 60)
    print("🕵️  SELECTOR FINDER TOOL")
    print("=" * 60)
    print("Instructions:")
    print("1. A browser window will open loaded with your URL.")
    print("2. A 'Playwright Inspector' window will also appear.")
    print("3. Click on the element you want to scrape in the browser.")
    print("4. In the Inspector, look at the code generated in the 'Target' or code window(s).")
    print("   (Ignore the 'import' lines and 'def run(playwright)...' boilerplate!)")
    print("5. Find the line that corresponds to your click, inside the run() function.")
    print("   It will look like:")
    print("     page.locator(\"div\").filter(has_text=\"...\").click()")
    print("     OR")
    print("     page.get_by_role(\"heading\", name=\"...\").click()")
    print("6. Copy just the selector part inside the parentheses (or the chain).")
    print("   Example: .title  OR  div >> text='Hello'")
    print("   Note: If it generates a complex chain, you might need to adapt it or pick a simpler element.")
    print("-" * 30)
    print("💡 TIP FOR LISTS (e.g., all products/quotes):")
    print("   The code above gives you a SINGLE item (e.g., the specific quote you clicked).")
    print("   To get ALL items:")
    print("   1. Use the 'Pick Locator' button (cursor icon) in the Inspector toolbar.")
    print("   2. Hover over the element to see its class name (e.g., div.quote).")
    print("   3. Use that class name as your selector.")
    print("-" * 30)
    print("=" * 60)
    print(f"Launching Playwright Codegen for: {args.url}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop if needed.\n")

    try:
        # Launch playwright codegen
        subprocess.run(["playwright", "codegen", args.url], check=True)
    except KeyboardInterrupt:
        print("\nExiting...")
    except subprocess.CalledProcessError as e:
        print(f"\nError occurred: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
