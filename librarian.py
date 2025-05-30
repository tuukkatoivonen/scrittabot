import base64
import io
import os
import re
import tokenizers
from PIL import Image

from typing import Optional

IMAGE_MAX_SIZE = 256
FILES_PATH = 'files'


class Tokenizer():
    class Tokens():
        def __init__(self, tokenizer, text: str):
            self._tokenizer = tokenizer
            self._tokens = self._tokenizer._tokenizer.encode(text)

        def count(self):
            return len(self._tokens)

    def __init__(self):
        tokenizer_json = 'tokenizer.json'
        self._tokenizer = tokenizers.Tokenizer.from_file(tokenizer_json)

    def tokenize(self, text: str):
        return self.Tokens(self, text)


class File():
    def __init__(self, librarian, unsecure_filename, filename, pathname):
        self._librarian = librarian
        self._unsecure_filename = unsecure_filename
        self._filename = filename
        self._pathname = pathname

    def unsecure_filename(self):
        return self._unsecure_filename

    def filename(self):
        return self._filename

    def type(self):
        return 'generic'

class FileText(File):
    def __init__(self, librarian, unsecure_filename, filename, pathname):
        super().__init__(librarian, unsecure_filename, filename, pathname)
        self._index()

    def type(self):
        return 'text'

    def _index(self):
        with open(self._pathname, 'r') as f:
            text = f.read()
            tokens = self._librarian.tokenizer.tokenize(text)
            print(f'Tokens: {tokens.count()}')

class FileImage(File):
    def __init__(self, librarian, unsecure_filename, filename, pathname):
        super().__init__(librarian, unsecure_filename, filename, pathname)
        self._max_size = IMAGE_MAX_SIZE
        self._image = Image.open(pathname)      # Raises exception of not valid image

    def type(self):
        return 'image'

    def content(self):
        # Scale image to reasonable size and return encoded for LLM
        img = self._image
        if self._image.width > self._max_size or self._image.height > self._max_size:
            scale_width  = self._max_size / self._image.width
            scale_height = self._max_size / self._image.height
            scale = min(scale_width, scale_height)
            new_width = max(int(self._image.width * scale_width), 8)
            new_height = max(int(self._image.height * scale_height), 8)
            img = self._image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Save image to a byte buffer in PNG format
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        # Base64 encode the image bytes
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return 'data:image/png;base64,' + base64_image


class Librarian():
    def __init__(self, path=FILES_PATH):
        self._path = path
        self._files = []
        os.makedirs(self._path, exist_ok=True)
        self.tokenizer = Tokenizer()

    def _pathname(self, filename):
        return self._path + '/' + filename

    def add_file(self, unsecure_filename: str, data: Optional[bytes] = None):
        # If data is None, file already exists, just import it.
        # If data is not None, create the file from the data.
        # Return the filename that can be used to refer to the file.
        filename = re.sub(r'[^A-Za-z0-9_=\.,-]', '_', unsecure_filename)[:100]

        if data:
            # File has to be created
            n = 0
            fn = filename
            while True:
                filename = fn + (f'-{n}' if n > 0 else '')
                pathname = self._pathname(filename)
                if not os.path.isfile(pathname):
                    break
                n += 1
            with open(pathname, 'wb') as f:
                f.write(data)

        pathname = self._pathname(filename)
        if not os.path.isfile(pathname):
            raise Exception('File does not exist')

        f = None
        for file_class in [ FileImage, FileText, File ]:
            try:
                f = file_class(self, unsecure_filename, filename, pathname)
                break
            except Exception as e:
                print(f'Fail: {e}')
        if f is None:
            raise Exception(f'Can not handle this file: {filename}')
        self._files.append(f)
        return f

# Tests
if __name__ == '__main__':
    tok = Tokenizer()
    t = tok.tokenize('The quick brown fox jumps over the lazy dog')
    print(f'Tokens: {t.count()}')

    lib = Librarian()
    f = lib.add_file('test_text.txt')
    print(f'File type: {f.type()}')

