from io import StringIO
import os

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

    def __str__(self):
        return self.text
