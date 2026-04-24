import os
import codecs

# Strategy 3: Register a custom error handler that replaces invalid bytes with a space
def replace_with_space(exc):
    if isinstance(exc, UnicodeDecodeError):
        # Return a space and skip the invalid byte (exc.start + 1)
        return (' ', exc.start + 1)
    raise TypeError("don't know how to handle %r" % exc)

codecs.register_error('replace_space', replace_with_space)


def check_encoding_strategies(directory):
    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist.")
        return

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath) and filepath.endswith('.txt'):
            try:
                # First try UTF-8 strictly
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # print(f"{filename}: OK (UTF-8)")
            except UnicodeDecodeError:
                # If it fails, we can try different strategies:

                # --- Strategy 1: Fallback to a common legacy encoding (e.g., windows-1252) ---
                try:
                    with open(filepath, 'r', encoding='windows-1252') as f:
                        content = f.read()
                    print(f"{filename}: Fixed by falling back to 'windows-1252'")
                    continue # It worked, move to next file
                except UnicodeDecodeError:
                    pass
                
                # --- Strategy 2: Use errors='replace' and then string replace ---
                # This replaces invalid characters with the standard Unicode replacement character  (\ufffd)
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                # Replace the  characters with spaces
                content_spaced = content.replace('\ufffd', ' ')
                print(f"{filename}: Read with errors='replace' + replaced  with space")

                # --- Strategy 3: Using the custom error handler defined above ---
                with open(filepath, 'r', encoding='utf-8', errors='replace_space') as f:
                    content = f.read()
                print(f"{filename}: Read natively replacing invalid bytes with spaces using custom handler")

if __name__ == "__main__":
    check_encoding_strategies('cfps')
