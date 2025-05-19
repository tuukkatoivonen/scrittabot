import json
import requests
import urllib3


class Llm:
    def __init__(self, url, api_key=None, options={}, embedding_query='', insecure=False):
        self.base_url = url
        self.api_key = api_key
        self.options = options
        self.insecure = insecure
        if self.insecure:
            urllib3.disable_warnings()
        self.embedding_query = embedding_query

        self.session = requests.Session()
        self.session.headers.update({ "Content-Type": "application/json" })
        if self.api_key:
            self.session.headers.update({ "Authorization": f"Bearer {self.api_key}" })

        self.current_response = None
        self.response_iterator = None

    def completion(self, messages):
        """
        Initiates a streaming request to the LLM.

        Args:
            messages (list): A list of message objects, e.g.,
                             [{"role": "system", "content": "You are helpful."},
                              {"role": "user", "content": "Hello!"}]
        Returns:
            bool: True if the request was initiated successfully, False otherwise.
        """
        if self.current_response:
            self.abort()  # Abort any existing stream

        payload = self.options
        payload['stream'] = True
        payload['messages'] = messages

        try:
            self.current_response = self.session.post(
                self.base_url + '/v1/chat/completions',
                json = payload,
                stream = True,
                verify = not self.insecure
            )
            self.current_response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            self.response_iterator = self.current_response.iter_lines()
        except requests.exceptions.RequestException as e:
            print(f"Error initiating request: {e}")
            self._cleanup_stream()
            return False
        return True

    def get_next_chunk(self):
        """
        Returns the next content chunk from the stream.

        Returns:
            str: The content of the next chunk (e.g., "Hello", " there").
            None: If there is no more data or an error occurred.
        """
        if not self.response_iterator:
            return None

        try:
            for line_bytes in self.response_iterator:
                if line_bytes:
                    line = line_bytes.decode('utf-8').strip()
                    # Standard SSE format: lines start with "data: "
                    if line.startswith("data:"):
                        data_content = line[len("data:"):].strip()
                        if data_content == "[DONE]": # OpenAI-specific end-of-stream marker
                            self._cleanup_stream()
                            return None
                        try:
                            chunk_json = json.loads(data_content)
                            choices = chunk_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content is not None: # Could be an empty string, which is valid
                                    return content
                                # If 'content' is not present (e.g. only 'role' in delta),
                                # it's still a valid chunk, but we are interested in text.
                                # Continue to the next line for more data.
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON from line: {data_content}")
                            continue # Skip malformed lines
                        except (IndexError, KeyError) as e:
                            print(f"Warning: Unexpected JSON structure: {data_content}, error: {e}")
                            continue # Skip lines with unexpected structure
                    # Lines that are not "data: ..." or empty lines are typically ignored in SSE
                    # or could be comments (starting with ':')
            
            # If the loop finishes, it means the iterator is exhausted
            self._cleanup_stream()
            return None

        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.StreamConsumedError):
            # These errors can occur if the stream is interrupted or already consumed
            print("Stream connection error or already consumed.")
            self._cleanup_stream()
            return None
        except StopIteration: # Should be handled by the loop completion, but good to be explicit
            self._cleanup_stream()
            return None
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred while fetching chunk: {e}")
            self._cleanup_stream()
            return None

    def _cleanup_stream(self):
        """Helper method to close response and clear iterators."""
        if self.current_response:
            self.current_response.close()
        self.current_response = None
        self.response_iterator = None

    def abort(self):
        """
        Aborts the current streaming request.
        """
        print("Aborting stream...")
        self._cleanup_stream()

    def count_tokens(self, string):
        payload = self.options
        payload['prompt'] = string
        response = self.session.post(
            self.base_url + '/utils/token_counter',
            json = payload,
            verify = not self.insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['total_tokens']

    def embedding(self, string):
        payload = self.options
        payload['input'] = self.embedding_query + string
        response = self.session.post(
            self.base_url + '/v1/embeddings',
            json = payload,
            verify = not self.insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['data'][0]['embedding']

    def __del__(self):
        """Ensure resources are cleaned up when the object is garbage collected."""
        self.abort()
        if self.session: # Check if session was initialized
            self.session.close()

class LlmLineStreaming:
    def __init__(self, llm: Llm):
        """
        Initializes the LineStreamingLLM, which wraps a StreamingLLM instance
        to provide line-by-line data retrieval.

        Args:
            streaming_api (StreamingLLM): An instance of StreamingLLM to use for fetching data.
        """
        if not isinstance(llm, Llm):
            raise TypeError("llm must be an instance of Llm")
        self.llm = llm
        self.line_buffer = "" # Buffer to accumulate chunks into lines

    def completion(self, messages):
        """
        Initiates a streaming request using the underlying StreamingLLM.
        Clears any existing line buffer.

        Args:
            messages (list): A list of message objects, e.g.,
                             [{"role": "system", "content": "You are helpful."},
                              {"role": "user", "content": "Hello!"}]
        Returns:
            bool: True if the request was initiated successfully, False otherwise.
        """
        self.line_buffer = ""  # Clear buffer for a new request
        return self.llm.completion(messages)

    def get_next_line(self):
        """
        Returns the next line of text from the stream.
        A line is defined as a sequence of characters accumulated from one or more
        chunks, ending either with a newline character ('\n') or at the end of
        the stream. The returned line does not include the trailing newline character.

        Note: While the prompt's example output for this method ("Hello", then " there")
        matches chunk-by-chunk behavior, this implementation adheres to the
        "line-by-line (separated by \n')" requirement, buffering chunks to form
        complete lines.

        Returns:
            str: The next line of text.
            None: If there is no more data to return.
        """
        while True:
            # Check if the existing buffer already contains a complete line
            if '\n' in self.line_buffer:
                line, rest = self.line_buffer.split('\n', 1)
                self.line_buffer = rest
                return line

            # If no newline in buffer, fetch more data from the underlying LLM
            chunk = self.llm.get_next_chunk()

            if chunk is None:  # Stream has ended
                if self.line_buffer:  # If there's anything left in the buffer, it's the last line
                    line_to_return = self.line_buffer
                    self.line_buffer = ""  # Clear buffer
                    return line_to_return
                else:  # Buffer is empty and stream ended
                    return None
            
            # Append the new chunk to the buffer
            if isinstance(chunk, str): # Should always be str or None from StreamingLLM
                self.line_buffer += chunk
            # else: This case should ideally not happen if StreamingLLM.get_next_chunk works as specified.
            # No specific handling needed if chunk is an empty string; it's just appended.

            # Loop will continue, and the next iteration will check for '\n' in the updated buffer.

    def abort(self):
        """
        Aborts the current request via the underlying StreamingLLM and clears the line buffer.
        """
        self.llm.abort()
        self.line_buffer = ""  # Clear buffer on abort
