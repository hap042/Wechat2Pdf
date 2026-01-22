import os
import subprocess
import sys
from pypdf import PdfReader

def run_tests():
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_urls_path = os.path.join(base_dir, "tests", "test_urls.txt")
    script_path = os.path.join(base_dir, "backend", "main.py")
    output_dir = os.path.join(base_dir, "output", "test_results")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Expected page counts for the test cases
    EXPECTED_PAGES = [11, 14, 8, 9]
    
    # Read URLs
    if not os.path.exists(test_urls_path):
        print(f"Error: Test URLs file not found at {test_urls_path}")
        return
        
    with open(test_urls_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
        
    print(f"Found {len(urls)} test cases.")
    
    passed = 0
    failed = 0
    
    for i, url in enumerate(urls):
        print(f"\nRunning Test Case {i+1}: {url}")
        pdf_name = f"test_result_{i+1}.pdf"
        pdf_path = os.path.join(output_dir, pdf_name)
        
        # Build command
        # Using --save-discarded to ensure we test that logic too
        cmd = [sys.executable, script_path, url, "--output", pdf_path, "--save-discarded"]
        
        try:
            # Run script
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Check if file exists and has size
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    try:
                        reader = PdfReader(pdf_path)
                        num_pages = len(reader.pages)
                        
                        expected = EXPECTED_PAGES[i] if i < len(EXPECTED_PAGES) else None
                        
                        if expected is not None:
                            if num_pages == expected:
                                print(f"✅ PASS: PDF generated at {pdf_path} ({os.path.getsize(pdf_path)//1024} KB) - Pages: {num_pages}")
                                passed += 1
                            else:
                                print(f"❌ FAIL: Page count mismatch. Expected {expected}, got {num_pages}")
                                print(f"Output: {result.stdout}")
                                failed += 1
                        else:
                            print(f"✅ PASS: PDF generated at {pdf_path} ({os.path.getsize(pdf_path)//1024} KB) - Pages: {num_pages} (No expectation set)")
                            passed += 1
                            
                    except Exception as e:
                        print(f"❌ FAIL: Could not read PDF pages: {e}")
                        failed += 1
                else:
                    print(f"❌ FAIL: Script succeeded but PDF missing or empty.")
                    print(f"Output: {result.stdout}")
                    failed += 1
            else:
                print(f"❌ FAIL: Script execution failed.")
                print(f"Stderr: {result.stderr}")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
            
    print(f"\n{'='*30}")
    print(f"Test Summary: {passed} Passed, {failed} Failed")
    print(f"{'='*30}")

if __name__ == "__main__":
    run_tests()
