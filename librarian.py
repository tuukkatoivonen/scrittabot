import base64
import io
import os
import re
import tokenizers
from PIL import Image
from typing import Optional

import llm

TEXT_MAX_SIZE = 4096
IMAGE_MAX_SIZE = 256
FILES_PATH = 'files'

class InvalidFileType(Exception):
    pass

class Tokenizer():
    class Tokens():
        def __init__(self, tokenizer, text: str):
            self._tokenizer = tokenizer
            self._tokens = self._tokenizer._tokenizer.encode(text)
            self._token_ratio = self.count() / len(text)    # Average number of tokens per original byte

        def count(self):
            # Return number of tokens
            return len(self._tokens)

        def text_pos(self, tokenpos: int):
            # Return byte position in original text given a token
            if tokenpos < 0 or tokenpos >= self.count():
                if tokenpos == self.count():
                    return self._tokens.offsets[-1][1]                 # One token beyond max
                raise Exception(f'Bad tokenpos {tokenpos} (must be in 0..{self.count()-1})')
            return self._tokens.offsets[tokenpos][0]

        def token_pos(self, textpos: int):
            # Return token position given byte position in original text
            if self.count() < 1 or textpos < 0 or textpos >= self._tokens.offsets[-1][1]:
                raise Exception('Bad textpos')              # Over limits
            if textpos >= self._tokens.offsets[-1][0]:
                return self.count() - 1                     # Last token
            est_textpos = 0
            est_tokpos = 0
            token_ratio = self._token_ratio
            abserror = self._tokens.offsets[-1][1] + 1      # Maximum possible error, must always decrease
            while True:
                # Check if we found the corresponding token, if so, abort search
                if self.text_pos(est_tokpos) <= textpos < self.text_pos(est_tokpos+1):
                    break

                # Calculate new estimate for the token position
                error = textpos - est_textpos
                if abs(error) >= abserror:
                    break
                new_tokpos = max(1, min(int(est_tokpos + token_ratio * error), self.count() - 2))
                new_textpos = self.text_pos(new_tokpos)
                if new_tokpos == est_tokpos:
                    break
                est_textpos = new_textpos
                est_tokpos = new_tokpos
                abserror = abs(error)

            # Final fixup
            while not (self.text_pos(est_tokpos) <= textpos < self.text_pos(est_tokpos+1)):
                est_tokpos += -1 if (self.text_pos(est_tokpos) > textpos) else 1

            return est_tokpos

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
        self._prompt = ('You are a document summarizer. The document may be too large to be processed '
                        'as one piece, so you will be given the document in smaller parts. Keep the same style as the original '
                        'document and try to include all facts from the original text. Summarize primarily by removing '
                        'redundant and generally known facts. Keep the summarized text length in less than half of the original.')
        self._max_size = TEXT_MAX_SIZE      # Max chunk size
        self._splitstrings = [ '\n# ','\n## ', '\n### ', '\n#### ', '\n\n', '.\n', '\n', '. ', '  ', ' ' ]
        self._index()
        # Contributed by: [@riakashyap](https://github.com/riakashyap)

    def type(self):
        return 'text'

    def _index(self):
        with open(self._pathname, 'r') as f:
            text = f.read()
        tokens = self._librarian.tokenizer.tokenize(text)
        chunks = []
        text_pos = 0
        token_pos = 0
        while token_pos < tokens.count():
            new_token_pos = min(token_pos + self._max_size, tokens.count() - 1)
            new_text_pos = tokens.text_pos(new_token_pos)
            if new_token_pos < tokens.count() - 5:
                for s in self._splitstrings:
                    sp = text.rfind(s, text_pos + int((new_text_pos-text_pos)/2), new_text_pos)
                    if sp != -1:
                        new_token_pos = tokens.token_pos(sp)
                        break
            else:
                # Final chunk
                new_token_pos = tokens.count()
            new_text_pos = tokens.text_pos(new_token_pos)
            content = text[text_pos:new_text_pos]
            messages = [{ 'role': 'system', 'content': self._prompt }]
            if len(chunks) > 0:
                messages += [{ 'role': 'user', 'content': chunks[-1]['content'] },
                             { 'role': 'assistant', 'content': chunks[-1]['summary'] }]
            messages.append({ 'role': 'user', 'content': content })
            summary = self._librarian.llm.completion(messages)
            chunks.append({ 'content': content,
                            'summary': summary,
                            'begin': text_pos,
                            'end': new_text_pos,
                            'depth': 0,
                            'parents': [],
                            'tokens': new_token_pos - token_pos })
            token_pos = new_token_pos
            text_pos = new_text_pos
        self._chunks = chunks

class FileImage(File):
    def __init__(self, librarian, unsecure_filename, filename, pathname):
        super().__init__(librarian, unsecure_filename, filename, pathname)
        self._max_size = IMAGE_MAX_SIZE
        try:
            self._image = Image.open(pathname)      # Raises exception of not valid image
        except:
            raise InvalidFileType('Not an image file')

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
    def __init__(self, config, path=FILES_PATH):
        self._path = path
        self._files = []
        os.makedirs(self._path, exist_ok=True)
        self.tokenizer = Tokenizer()
        options = {
            'max_tokens': 4096,
            'temperature': 0.8,
            'top_p': 1.0,
            'n': 1,
            'cache_prompt': True,
            'model': config['model_llm'],
        }
        self.llm = llm.Llm(config['openai_url'], config['openai_key'], options, insecure=True)

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
            except InvalidFileType as e:
                print(f'Fail: {e}')
        if f is None:
            raise Exception(f'Can not handle this file: {filename}')
        self._files.append(f)
        return f

# Tests
if __name__ == '__main__':
    with open('config.json', 'r') as f:
        import json
        config = json.load(f)

    tok = Tokenizer()
    t = tok.tokenize('The quick brown fox jumps over the lazy dog')
    print(f'Tokens: {t.count()}')

    lib = Librarian(config)
    f = lib.add_file('test_text.txt')
    print(f'File type: {f.type()}')
    import pprint
    pprint.pp(f._chunks)

