#!/bin/bash
# Database initialization script
# Runs automatically when PostgreSQL container starts

set -e

echo "Creating legal review database schema..."

# Create extensions if they don't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";

    -- Projects table
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
        field_template_id INTEGER,
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Documents table
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        filename VARCHAR(255) NOT NULL,
        file_format VARCHAR(20) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        file_size_bytes INTEGER,
        status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
        chunk_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    -- Document chunks table
    CREATE TABLE IF NOT EXISTS document_chunks (
        id SERIAL PRIMARY KEY,
        document_id INTEGER NOT NULL,
        chunk_text TEXT NOT NULL,
        page_number INTEGER,
        section_title VARCHAR(255),
        chunk_index INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
    );

    -- Field templates table
    CREATE TABLE IF NOT EXISTS field_templates (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        fields JSONB NOT NULL DEFAULT '[]',
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Extraction results table
    CREATE TABLE IF NOT EXISTS extraction_results (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        field_name VARCHAR(255) NOT NULL,
        field_type VARCHAR(50) NOT NULL,
        extracted_value TEXT,
        raw_text TEXT,
        normalized_value TEXT,
        confidence_score DECIMAL(3,2),
        status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
    );

    -- Citations table
    CREATE TABLE IF NOT EXISTS citations (
        id SERIAL PRIMARY KEY,
        extraction_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        citation_text TEXT,
        relevance_score DECIMAL(3,2),
        page_number INTEGER,
        document_chunk_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(extraction_id) REFERENCES extraction_results(id) ON DELETE CASCADE,
        FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
    );

    -- Review states table
    CREATE TABLE IF NOT EXISTS review_states (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        extraction_id INTEGER NOT NULL,
        ai_value TEXT,
        manual_value TEXT,
        status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
        reviewed_by VARCHAR(255),
        reviewed_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY(extraction_id) REFERENCES extraction_results(id) ON DELETE CASCADE
    );

    -- Annotations table
    CREATE TABLE IF NOT EXISTS annotations (
        id SERIAL PRIMARY KEY,
        extraction_id INTEGER NOT NULL,
        annotation_text TEXT,
        highlighted_text TEXT,
        page_number INTEGER,
        created_by VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(extraction_id) REFERENCES extraction_results(id) ON DELETE CASCADE
    );

    -- Evaluation results table
    CREATE TABLE IF NOT EXISTS evaluation_results (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL,
        field_name VARCHAR(255) NOT NULL,
        document_id INTEGER,
        ai_value TEXT,
        human_value TEXT,
        is_match BOOLEAN,
        similarity_score DECIMAL(3,2),
        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    -- Tasks table
    CREATE TABLE IF NOT EXISTS background_tasks (
        id SERIAL PRIMARY KEY,
        task_id VARCHAR(255) UNIQUE NOT NULL,
        project_id INTEGER,
        task_type VARCHAR(100) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
        progress INTEGER DEFAULT 0,
        result JSONB,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
    CREATE INDEX IF NOT EXISTS idx_extraction_project_id ON extraction_results(project_id);
    CREATE INDEX IF NOT EXISTS idx_extraction_document_id ON extraction_results(document_id);
    CREATE INDEX IF NOT EXISTS idx_extraction_status ON extraction_results(status);
    CREATE INDEX IF NOT EXISTS idx_review_project_id ON review_states(project_id);
    CREATE INDEX IF NOT EXISTS idx_review_status ON review_states(status);
    CREATE INDEX IF NOT EXISTS idx_citation_extraction_id ON citations(extraction_id);
    CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
    CREATE INDEX IF NOT EXISTS idx_evaluation_project_id ON evaluation_results(project_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON background_tasks(project_id);

    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$POSTGRES_USER";
EOSQL

echo "Database initialization completed successfully!"
