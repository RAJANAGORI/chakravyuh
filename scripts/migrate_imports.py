#!/usr/bin/env python3
"""Script to update imports after reorganization."""
import os
import re
from pathlib import Path

# Import mapping: old -> new
IMPORT_MAPPINGS = {
    # Core
    r'from core\.': 'from chakravyuh.core.',
    r'import core\.': 'import chakravyuh.core.',
    
    # Utils
    r'from utils\.': 'from chakravyuh.utils.',
    r'import utils\.': 'import chakravyuh.utils.',
    
    # Retrieval
    r'from rag_retriever\.': 'from chakravyuh.retrieval.',
    r'import rag_retriever\.': 'import chakravyuh.retrieval.',
    
    # Verification
    r'from verification\.': 'from chakravyuh.verification.',
    r'import verification\.': 'import chakravyuh.verification.',
    
    # Specific verification submodules
    r'from verification\.claim_validator': 'from chakravyuh.verification.claims.validator',
    r'from verification\.evidence_grounding': 'from chakravyuh.verification.evidence.grounder',
    r'from verification\.confidence_scorer': 'from chakravyuh.verification.confidence.scorer',
    r'from verification\.source_scorer': 'from chakravyuh.verification.sources.scorer',
    r'from verification\.conflict_detector': 'from chakravyuh.verification.sources.conflict_detector',
    
    # Generation/QA
    r'from qa\.': 'from chakravyuh.generation.chains.',
    r'import qa\.': 'import chakravyuh.generation.chains.',
    
    # Storage
    r'from vectorstores\.': 'from chakravyuh.storage.vector.',
    r'import vectorstores\.': 'import chakravyuh.storage.vector.',
    
    # Connectors
    r'from connectors\.': 'from chakravyuh.connectors.',
    r'import connectors\.': 'import chakravyuh.connectors.',
    
    # Ingestion
    r'from ingestion\.': 'from chakravyuh.ingestion.',
    r'import ingestion\.': 'import chakravyuh.ingestion.',
}

# Specific file mappings
FILE_SPECIFIC_MAPPINGS = {
    'utils.tokenizer': 'chakravyuh.utils.tokenization',
    'utils.embeddings': 'chakravyuh.utils.embeddings',
    'utils.hash_utils': 'chakravyuh.utils.hashing',
    'utils.url_utils': 'chakravyuh.utils.urls',
    'utils.db_utils': 'chakravyuh.utils.db_utils',
    'utils.config_loader': 'chakravyuh.utils.config_loader',
    'utils.document_versioning': 'chakravyuh.verification.versioning.manager',
}

def update_imports_in_file(file_path: Path) -> bool:
    """Update imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply general mappings
        for old_pattern, new_pattern in IMPORT_MAPPINGS.items():
            content = re.sub(old_pattern, new_pattern, content)
        
        # Apply file-specific mappings
        for old_import, new_import in FILE_SPECIFIC_MAPPINGS.items():
            content = re.sub(
                rf'from {re.escape(old_import)}',
                f'from {new_import}',
                content
            )
            content = re.sub(
                rf'import {re.escape(old_import)}',
                f'import {new_import}',
                content
            )
        
        # Only write if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Update imports in all Python files."""
    base_dir = Path(__file__).parent.parent
    
    # Files to update (in new structure)
    files_to_update = [
        base_dir / 'chakravyuh',
        base_dir / 'scripts',
        base_dir / 'tests',
    ]
    
    updated_count = 0
    for directory in files_to_update:
        if not directory.exists():
            continue
            
        for py_file in directory.rglob('*.py'):
            if update_imports_in_file(py_file):
                print(f"Updated: {py_file.relative_to(base_dir)}")
                updated_count += 1
    
    print(f"\nUpdated {updated_count} files")

if __name__ == '__main__':
    main()
