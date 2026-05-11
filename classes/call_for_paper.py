from io import StringIO
import os
import re

class CallForPaper:
    def __init__(self, source):
        if hasattr(source, "getvalue"):
            decoded_string = source.getvalue().decode("utf-8", errors="replace").replace('\ufffd', ' ')
            stringio = StringIO(decoded_string)
            self.text = stringio.read()
        elif isinstance(source, str) and os.path.exists(source):
            with open(source, 'r', encoding='utf-8', errors='replace') as f:
                self.text = f.read().replace('\ufffd', ' ')
        elif isinstance(source, str):
            self.text = source
        else:
            self.text = str(source)

    def clean(self):
        """Placeholder for any future text cleaning routines."""
        pass

    def get_rendered_html(self) -> str:
        import html
        text = html.escape(self.text)
        
        # Convert leading tabs or spaces to bullet points
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            stripped_line = line.lstrip(' \t')
            if not stripped_line:
                new_lines.append(line)
                continue
                
            leading_whitespace = line[:len(line) - len(stripped_line)]
            # Assume 1 tab = 4 spaces
            space_count = leading_whitespace.replace('\t', '    ').count(' ')
            indent_level = space_count // 4
            
            # Check if line already starts with a list marker (bullet or number)
            has_bullet = bool(re.match(r'^([-*•◦▪]|\d+\.)\s', stripped_line))
            
            if indent_level > 0 and not has_bullet:
                if indent_level == 1:
                    bullet = '• '
                elif indent_level == 2:
                    bullet = '◦ '
                else:
                    bullet = '▪ '
                line = ('    ' * (indent_level - 1)) + bullet + stripped_line
            else:
                # Normalize any existing indentation to raw spaces
                line = (' ' * space_count) + stripped_line
                
            new_lines.append(line)
            
        text = '\n'.join(new_lines)
        
        # Find URLs and convert them to clickable links
        url_pattern = re.compile(r'(https?://[^\s&]+)')
        text = url_pattern.sub(r'<a href="\1" target="_blank">\1</a>', text)
        
        # Find emails and convert them to mailto links
        email_pattern = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
        text = email_pattern.sub(r'<a href="mailto:\1">\1</a>', text)
        
        return f"<div style='white-space: pre-wrap; font-family: monospace; background-color: #f4f6f9; padding: 15px; border-radius: 5px; border: 1px solid #ddd;'>{text}</div>"

    def __str__(self):
        return self.text
