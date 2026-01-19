#!/usr/bin/env python3
"""Fix all imports in the reorganized structure."""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

IMPORT_FIXES = [
    # Core imports
    (r'from core\.', 'from chakravyuh.core.'),
    (r'import core\.', 'import chakravyuh.core.'),
    (r'from chakravyuh.core import', 'from chakravyuh.core import'),
    
    # Utils imports
    (r'from utils\.', 'from chakravyuh.utils.'),
    (r'import utils\.', 'import chakravyuh.utils.'),
    (r'from chakravyuh.utils import', 'from chakravyuh.utils import'),
    
    # Retrieval imports
    (r'from rag_retriever\.', 'from chakravyuh.retrieval.'),
    (r'import rag_retriever\.', 'import chakravyuh.retrieval.'),
    (r'from chakravyuh.retrieval import', 'from chakravyuh.retrieval import'),
    
    # Verification imports - specific submodules
    (r'from verification\.claim_validator', 'from chakravyuh.verification.claims.validator'),
    (r'from verification\.evidence_grounding', 'from chakravyuh.verification.evidence.grounder'),
    (r'from verification\.confidence_scorer', 'from chakravyuh.verification.confidence.scorer'),
    (r'from verification\.source_scorer', 'from chakravyuh.verification.sources.scorer'),
    (r'from verification\.conflict_detector', 'from chakravyuh.verification.sources.conflict_detector'),
    (r'from verification\.', 'from chakravyuh.verification.'),
    (r'import verification\.', 'import chakravyuh.verification.'),
    
    # Generation/QA imports
    (r'from qa\.', 'from chakravyuh.generation.chains.'),
    (r'import qa\.', 'import chakravyuh.generation.chains.'),
    
    # Storage imports
    (r'from vectorstores\.', 'from chakravyuh.storage.vector.'),
    (r'import vectorstores\.', 'import chakravyuh.storage.vector.'),
    
    # Connector imports
    (r'from connectors\.', 'from chakravyuh.connectors.'),
    (r'import connectors\.', 'import chakravyuh.connectors.'),
    
    # Ingestion imports
    (r'from ingestion\.', 'from chakravyuh.ingestion.'),
    (r'import ingestion\.', 'import chakravyuh.ingestion.'),
    
    # Specific utility imports
    (r'from utils\.tokenizer', 'from chakravyuh.utils.tokenization'),
    (r'from utils\.hash_utils', 'from chakravyuh.utils.hashing'),
    (r'from utils\.url_utils', 'from chakravyuh.utils.urls'),
    (r'from utils\.document_versioning', 'from chakravyuh.verification.versioning.manager'),
    
    # Config path fixes
    (r'load_config\("config\.yaml"\)', 'load_config("config/config.yaml")'),
    (r'load_config\(path="config\.yaml"\)', 'load_config(path="config/config.yaml")'),
]

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        for pattern, replacement in IMPORT_FIXES:
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix imports in all Python files."""
    updated = 0
    
    # Fix files in chakravyuh package
    chakravyuh_dir = BASE_DIR / 'chakravyuh'
    if chakravyuh_dir.exists():
        for py_file in chakravyuh_dir.rglob('*.py'):
            if fix_imports_in_file(py_file):
                print(f"✓ Fixed: {py_file.relative_to(BASE_DIR)}")
                updated += 1
    
    # Fix files in scripts
    scripts_dir = BASE_DIR / 'scripts'
    if scripts_dir.exists():
        for py_file in scripts_dir.rglob('*.py'):
            if fix_imports_in_file(py_file):
                print(f"✓ Fixed: {py_file.relative_to(BASE_DIR)}")
                updated += 1
    
    print(f"\n✅ Updated {updated} files")

if __name__ == '__main__':
    main()
