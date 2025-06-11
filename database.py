#!/usr/bin/env python3

import hashlib
import psycopg2
import psycopg2.extras      # dictionary cursors
import urllib.parse
from pgvector.psycopg2 import register_vector

import llm

EMBEDDING_DIMENSIONS = 1024

# Create initially the database manually as follows:
#  su postgres -c psql
#  CREATE USER scrittabot WITH LOGIN PASSWORD 'a_secure_password';
#  CREATE DATABASE scrittabot OWNER scrittabot;
#  GRANT CONNECT ON DATABASE scrittabot TO scrittabot;
#  \c scrittabot
#  CREATE EXTENSION vector;

DROP_TABLES_SQL = """
DROP TABLE IF EXISTS edges CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
"""

CREATE_CHUNKS_TABLE_SQL = f"""
CREATE TABLE chunks (
    key SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    chunk_begin BIGINT NOT NULL CHECK (chunk_begin >= 0),
    chunk_end BIGINT NOT NULL CHECK (chunk_end >= 0),
    depth INTEGER NOT NULL CHECK (depth > 0),
    original_filename TEXT NOT NULL,
    original_begin BIGINT NOT NULL CHECK (original_begin >= 0),
    original_end BIGINT NOT NULL CHECK (original_end >= 0),
    sha256 VARCHAR(64) NOT NULL, -- SHA256 is 64 hex characters
    embedding VECTOR({EMBEDDING_DIMENSIONS}),
    keywords TEXT[],
    created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    access_count BIGINT DEFAULT 0 NOT NULL CHECK (access_count >= 0),

    -- Cross-column checks
    CHECK (chunk_end >= chunk_begin),
    CHECK (original_end >= original_begin)
);
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
"""

CREATE_EDGES_TABLE_SQL = """
CREATE TABLE edges (
    chunk_from BIGINT NOT NULL,
    chunk_to BIGINT NOT NULL,
    type VARCHAR(50) NOT NULL,      -- e.g., 'parent', 'previous', 'next', 'supports'
    strength DOUBLE PRECISION NOT NULL,

    PRIMARY KEY (chunk_from, chunk_to),

    -- Foreign key constraints
    FOREIGN KEY (chunk_from) REFERENCES chunks(key) ON DELETE CASCADE,
    FOREIGN KEY (chunk_to) REFERENCES chunks(key) ON DELETE CASCADE
);
"""

class Database():
    def __init__(self, config):
        url = urllib.parse.urlparse(config['database_url'])
        if url.scheme != 'postgresql':
            raise Exception('Bad database url')
        params = {
            'database': url.path.lstrip('/'),
            'user':     url.username,
            'password': url.password,
            'host':     url.hostname,
            'port':     url.port,
            'sslmode':  'prefer',
        }
        for k in params.keys():
            if not params[k]:
                del params[k]
        print(f'Connecting to database "{params["database"]}"')
        self._db = psycopg2.connect(**params)
        with self._db.cursor() as cur:
             cur.execute("SET TIMEZONE TO 'UTC';")
             self._db.commit()
        register_vector(self._db)
        if not self._check():
            print('Creating new database')
            self.reset()
        options = { 'model': config['model_embedding'] }
        self._llm = llm.Llm(config['openai_url'], config['openai_key'], options, insecure=True)

    def __del__(self):
        self._db.close()

    def _check(self):
        # Check that the relations exist, create if not
        # We count how many of the specified table names exist as 'r' (regular table) in the given schema.
        schema_name = 'public'
        table_names = ( 'chunks', 'edges' )
        sql_query = """
            SELECT COUNT(*)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
            AND n.nspname = %s
            AND c.relname IN %s;
        """
        try:
            with self._db.cursor() as cur:
                # Execute the query, passing schema_name and table_names as parameters
                # psycopg2 automatically handles the list/tuple for the IN clause
                cur.execute(sql_query, (schema_name, table_names))
                count = cur.fetchone()[0]
                return count == len(table_names)
        except psycopg2.Error as e:
            print(f'Error checking for table existence: {e}')
            return False

    def reset(self):
        try:
            with self._db.cursor() as cur:
                cur.execute(DROP_TABLES_SQL)
                cur.execute(CREATE_CHUNKS_TABLE_SQL)
                cur.execute(CREATE_EDGES_TABLE_SQL)
            self._db.commit()
            print(f'Database resetted successfully')
        except psycopg2.Error as e:
            self._db.rollback()
            print(f'Error resetting database ({e}), rolled back')
            raise e

    def add_chunk(self, chunk):
        # chunk: must contain fields below AND 'content'
        # Adds 'embedding', 'sha256', and 'key', also returns key
        insert_sql = """
            INSERT INTO chunks (
                filename,
                chunk_begin,
                chunk_end,
                depth,
                original_filename,
                original_begin,
                original_end,
                sha256,
                embedding,
                keywords
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            ) RETURNING key;
        """
        chunk['embedding'] = self._llm.embedding(chunk['content'])
        chunk['sha256'] = hashlib.sha256(chunk['content'].encode('utf-8')).hexdigest()
        with self._db.cursor() as cur:
            data = (
                chunk.get('filename'),
                chunk.get('chunk_begin'),
                chunk.get('chunk_end'),
                chunk.get('depth'),
                chunk.get('original_filename'),
                chunk.get('original_begin'),
                chunk.get('original_end'),
                chunk.get('sha256'),
                chunk.get('embedding'),
                chunk.get('keywords'),
            )
            cur.execute(insert_sql, data)
            key = cur.fetchone()[0]
            self._db.commit()
        chunk['key'] = key
        return key


if __name__ == '__main__':
    import yaml
    import sys

    CONFIG_FILE = 'config.yaml'
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)

    db = Database(config)

    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        # Reset database. Destroys all existing data.
        print('Resetting database')
        db.reset()
