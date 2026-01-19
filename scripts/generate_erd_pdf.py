#!/usr/bin/env python3
"""
Generate a detailed ERD (Entity Relationship Diagram) PDF document for Chakravyuh RAG system.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not available. Using matplotlib fallback.")
    import matplotlib
    matplotlib.use('PDF')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    import numpy as np


def create_erd_with_reportlab(output_path):
    """Create ERD PDF using reportlab."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#283593'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#3949ab'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    # Title
    elements.append(Paragraph("Chakravyuh RAG System", title_style))
    elements.append(Paragraph("Entity Relationship Diagram (ERD)", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Table of Contents
    elements.append(Paragraph("Table of Contents", heading_style))
    toc_items = [
        "1. Overview",
        "2. Core Database Schema",
        "3. Knowledge Graph Entities",
        "4. MITRE ATT&CK Entities",
        "5. CVE/CWE Entities",
        "6. Security & Audit Entities",
        "7. Evaluation Entities",
        "8. Relationships Summary"
    ]
    for item in toc_items:
        elements.append(Paragraph(item, styles['Normal']))
    elements.append(PageBreak())
    
    # 1. Overview
    elements.append(Paragraph("1. Overview", heading_style))
    overview_text = """
    The Chakravyuh RAG system implements a layered architecture for secure knowledge retrieval and threat modeling.
    This ERD documents all entities, their attributes, and relationships within the system.
    """
    elements.append(Paragraph(overview_text, styles['Normal']))
    elements.append(Paragraph("<b>Key Components:</b>", styles['Normal']))
    elements.append(Paragraph("• Core Database: PostgreSQL with pgvector for document storage and similarity search", styles['Normal']))
    elements.append(Paragraph("• Knowledge Graph: Threat intelligence graph with nodes and edges", styles['Normal']))
    elements.append(Paragraph("• MITRE ATT&CK: Technique, Tactic, and Procedure entities", styles['Normal']))
    elements.append(Paragraph("• CVE/CWE: Vulnerability and weakness enumeration", styles['Normal']))
    elements.append(Paragraph("• Security: Audit logs and access control", styles['Normal']))
    elements.append(Paragraph("• Evaluation: Benchmark datasets and review storage", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # 2. Core Database Schema
    elements.append(Paragraph("2. Core Database Schema", heading_style))
    
    elements.append(Paragraph("2.1 Documents Table", subheading_style))
    doc_table_data = [
        ['Column', 'Type', 'Description', 'Constraints'],
        ['id', 'SERIAL', 'Primary key', 'PRIMARY KEY, NOT NULL'],
        ['content', 'TEXT', 'Document text content', 'NOT NULL'],
        ['metadata', 'JSONB', 'Document metadata (service, url, etc.)', 'NULL'],
        ['embedding', 'VECTOR(1536)', 'OpenAI embedding vector', 'NULL']
    ]
    doc_table = Table(doc_table_data, colWidths=[1.2*inch, 1.5*inch, 3*inch, 2*inch])
    doc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3949ab')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    elements.append(doc_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("2.2 Document Hashes Table", subheading_style))
    hash_table_data = [
        ['Column', 'Type', 'Description', 'Constraints'],
        ['id', 'SERIAL', 'Primary key', 'PRIMARY KEY, NOT NULL'],
        ['doc_name', 'TEXT', 'Document name/identifier', 'NOT NULL'],
        ['service', 'TEXT', 'Service name (s3, ec2, etc.)', 'NOT NULL'],
        ['sha256', 'TEXT', 'SHA256 hash of document', 'NOT NULL'],
        ['updated_at', 'TIMESTAMP', 'Last update timestamp', 'DEFAULT NOW()'],
        ['', '', 'Unique constraint', 'UNIQUE(doc_name, service)']
    ]
    hash_table = Table(hash_table_data, colWidths=[1.2*inch, 1.5*inch, 3*inch, 2*inch])
    hash_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3949ab')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    elements.append(hash_table)
    elements.append(PageBreak())
    
    # 3. Knowledge Graph Entities
    elements.append(Paragraph("3. Knowledge Graph Entities", heading_style))
    
    elements.append(Paragraph("3.1 ThreatNode Entity", subheading_style))
    node_text = """
    Represents nodes in the threat intelligence graph. Each node can be one of the following types:
    """
    elements.append(Paragraph(node_text, styles['Normal']))
    elements.append(Paragraph("• THREAT: Security threats", styles['Normal']))
    elements.append(Paragraph("• ASSET: System assets", styles['Normal']))
    elements.append(Paragraph("• CONTROL: Security controls", styles['Normal']))
    elements.append(Paragraph("• VULNERABILITY: System vulnerabilities", styles['Normal']))
    elements.append(Paragraph("• TECHNIQUE: MITRE ATT&CK techniques", styles['Normal']))
    elements.append(Paragraph("• CVE: Common Vulnerabilities and Exposures", styles['Normal']))
    elements.append(Paragraph("• CWE: Common Weakness Enumeration", styles['Normal']))
    
    node_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['node_id', 'str', 'Unique node identifier'],
        ['node_type', 'NodeType (enum)', 'Type of node (threat, asset, control, etc.)'],
        ['name', 'str', 'Node name'],
        ['description', 'str (optional)', 'Node description'],
        ['metadata', 'Dict[str, Any]', 'Additional metadata'],
        ['risk_score', 'float (optional)', 'Risk score from 0.0 to 1.0']
    ]
    node_table = Table(node_table_data, colWidths=[1.5*inch, 2*inch, 4.5*inch])
    node_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(node_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("3.2 ThreatEdge Entity", subheading_style))
    edge_text = """
    Represents relationships between nodes in the threat graph.
    """
    elements.append(Paragraph(edge_text, styles['Normal']))
    
    edge_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['edge_id', 'str', 'Unique edge identifier'],
        ['source_id', 'str', 'Source node ID'],
        ['target_id', 'str', 'Target node ID'],
        ['edge_type', 'EdgeType (enum)', 'Type: exploits, mitigates, affects, related_to, precedes, causes'],
        ['weight', 'float', 'Relationship strength (default: 1.0)'],
        ['metadata', 'Dict[str, Any]', 'Additional edge metadata']
    ]
    edge_table = Table(edge_table_data, colWidths=[1.5*inch, 2*inch, 4.5*inch])
    edge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(edge_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("3.3 AttackPath Entity", subheading_style))
    path_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['path_id', 'str', 'Unique path identifier'],
        ['nodes', 'List[str]', 'Ordered list of node IDs in the path'],
        ['edges', 'List[str]', 'Ordered list of edge IDs in the path'],
        ['total_risk', 'float', 'Total risk score for the path'],
        ['description', 'str (optional)', 'Path description']
    ]
    path_table = Table(path_table_data, colWidths=[1.5*inch, 2*inch, 4.5*inch])
    path_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(path_table)
    elements.append(PageBreak())
    
    # 4. MITRE ATT&CK Entities
    elements.append(Paragraph("4. MITRE ATT&CK Entities", heading_style))
    
    elements.append(Paragraph("4.1 ATTACKTechnique Entity", subheading_style))
    technique_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['technique_id', 'str', 'MITRE technique ID (e.g., "T1001")'],
        ['name', 'str', 'Technique name'],
        ['description', 'str', 'Detailed description'],
        ['tactics', 'List[str]', 'Associated tactics (e.g., ["Initial Access"])'],
        ['platforms', 'List[str]', 'Target platforms (e.g., ["Windows", "Linux"])'],
        ['kill_chain_phases', 'List[str]', 'Kill chain phases'],
        ['data_sources', 'List[str]', 'Relevant data sources'],
        ['detection_rules', 'List[str]', 'Detection rules'],
        ['mitigations', 'List[str]', 'Mitigation strategies'],
        ['references', 'List[str]', 'Reference URLs'],
        ['created', 'datetime (optional)', 'Creation timestamp'],
        ['modified', 'datetime (optional)', 'Last modification timestamp']
    ]
    technique_table = Table(technique_table_data, colWidths=[1.8*inch, 2*inch, 4.2*inch])
    technique_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7b1fa2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    elements.append(technique_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("4.2 ATTACKTactic Entity", subheading_style))
    tactic_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['tactic_id', 'str', 'MITRE tactic ID (e.g., "TA0001")'],
        ['name', 'str', 'Tactic name'],
        ['description', 'str', 'Tactic description'],
        ['techniques', 'List[str]', 'List of associated technique IDs']
    ]
    tactic_table = Table(tactic_table_data, colWidths=[1.8*inch, 2*inch, 4.2*inch])
    tactic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7b1fa2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(tactic_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("4.3 ATTACKProcedure Entity", subheading_style))
    procedure_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['procedure_id', 'str', 'Unique procedure identifier'],
        ['technique_id', 'str', 'Associated technique ID'],
        ['name', 'str', 'Procedure name'],
        ['description', 'str', 'Procedure description'],
        ['actor', 'str (optional)', 'Threat actor name'],
        ['tools', 'List[str]', 'Tools used in procedure'],
        ['examples', 'List[str]', 'Example implementations'],
        ['references', 'List[str]', 'Reference URLs']
    ]
    procedure_table = Table(procedure_table_data, colWidths=[1.8*inch, 2*inch, 4.2*inch])
    procedure_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7b1fa2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(procedure_table)
    elements.append(PageBreak())
    
    # 5. CVE/CWE Entities
    elements.append(Paragraph("5. CVE/CWE Entities", heading_style))
    
    elements.append(Paragraph("5.1 CVE Entity", subheading_style))
    cve_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['cve_id', 'str', 'CVE identifier (e.g., "CVE-2024-1234")'],
        ['description', 'str', 'Vulnerability description'],
        ['published_date', 'datetime (optional)', 'Publication date'],
        ['modified_date', 'datetime (optional)', 'Last modification date'],
        ['cvss_score', 'float (optional)', 'CVSS score'],
        ['cvss_severity', 'str (optional)', 'Severity: CRITICAL, HIGH, MEDIUM, LOW'],
        ['affected_products', 'List[str]', 'List of affected products'],
        ['cwe_ids', 'List[str]', 'Associated CWE IDs'],
        ['attack_techniques', 'List[str]', 'Related MITRE ATT&CK technique IDs'],
        ['references', 'List[str]', 'Reference URLs'],
        ['mitigations', 'List[str]', 'Mitigation strategies']
    ]
    cve_table = Table(cve_table_data, colWidths=[1.8*inch, 2*inch, 4.2*inch])
    cve_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d32f2f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightcoral),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    elements.append(cve_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("5.2 CWE Entity", subheading_style))
    cwe_table_data = [
        ['Attribute', 'Type', 'Description'],
        ['cwe_id', 'str', 'CWE identifier (e.g., "CWE-79")'],
        ['name', 'str', 'Weakness name'],
        ['description', 'str', 'Detailed description'],
        ['weakness_abstraction', 'str (optional)', 'Base, Variant, Class, or Pillar'],
        ['status', 'str (optional)', 'Draft, Incomplete, or Stable'],
        ['related_weaknesses', 'List[str]', 'Related CWE IDs'],
        ['related_cves', 'List[str]', 'Related CVE IDs'],
        ['attack_techniques', 'List[str]', 'Related MITRE ATT&CK technique IDs']
    ]
    cwe_table = Table(cwe_table_data, colWidths=[1.8*inch, 2*inch, 4.2*inch])
    cwe_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d32f2f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightcoral),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(cwe_table)
    elements.append(PageBreak())
    
    # 6. Security & Audit Entities
    elements.append(Paragraph("6. Security & Audit Entities", heading_style))
    
    elements.append(Paragraph("6.1 Audit Log Entity", subheading_style))
    audit_text = """
    Audit logs are stored in the filesystem at the path specified in config (audit_log_dir).
    Each log entry typically contains:
    """
    elements.append(Paragraph(audit_text, styles['Normal']))
    elements.append(Paragraph("• timestamp: When the action occurred", styles['Normal']))
    elements.append(Paragraph("• user: User or system that performed the action", styles['Normal']))
    elements.append(Paragraph("• action: Type of action (query, access, modification, etc.)", styles['Normal']))
    elements.append(Paragraph("• resource: Resource accessed", styles['Normal']))
    elements.append(Paragraph("• result: Success or failure", styles['Normal']))
    elements.append(Paragraph("• metadata: Additional context", styles['Normal']))
    
    audit_table_data = [
        ['Field', 'Type', 'Description'],
        ['timestamp', 'datetime', 'Action timestamp'],
        ['user', 'str', 'User identifier'],
        ['action', 'str', 'Action type'],
        ['resource', 'str', 'Resource accessed'],
        ['result', 'str', 'Success/Failure'],
        ['metadata', 'dict', 'Additional context']
    ]
    audit_table = Table(audit_table_data, colWidths=[1.5*inch, 2*inch, 4.5*inch])
    audit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f57c00')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(audit_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("6.2 Access Control Entity", subheading_style))
    access_text = """
    Access control is managed through configuration and runtime checks. Key components:
    """
    elements.append(Paragraph(access_text, styles['Normal']))
    elements.append(Paragraph("• User Roles: Different permission levels", styles['Normal']))
    elements.append(Paragraph("• Resource Permissions: Access rights for different resources", styles['Normal']))
    elements.append(Paragraph("• Policy Enforcement: Runtime access control checks", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("6.3 PII Detection Entity", subheading_style))
    pii_text = """
    PII (Personally Identifiable Information) detection and masking:
    """
    elements.append(Paragraph(pii_text, styles['Normal']))
    elements.append(Paragraph("• Detection: Identifies PII in documents and queries", styles['Normal']))
    elements.append(Paragraph("• Masking: Masks sensitive information before processing", styles['Normal']))
    elements.append(Paragraph("• Types: Email, SSN, credit cards, phone numbers, etc.", styles['Normal']))
    elements.append(PageBreak())
    
    # 7. Evaluation Entities
    elements.append(Paragraph("7. Evaluation Entities", heading_style))
    
    elements.append(Paragraph("7.1 Benchmark Dataset Entity", subheading_style))
    benchmark_text = """
    Benchmark datasets are stored as JSON files. Each benchmark case contains:
    """
    elements.append(Paragraph(benchmark_text, styles['Normal']))
    
    benchmark_table_data = [
        ['Field', 'Type', 'Description'],
        ['case_id', 'str', 'Unique case identifier'],
        ['architecture_description', 'str', 'System architecture description'],
        ['expected_threats', 'List[dict]', 'Expected threats with category, risk, impact, likelihood'],
        ['expected_controls', 'List[str]', 'Expected security controls'],
        ['expected_risks', 'List[str]', 'Expected risk items'],
        ['metadata', 'dict', 'Additional metadata']
    ]
    benchmark_table = Table(benchmark_table_data, colWidths=[2*inch, 2*inch, 4*inch])
    benchmark_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#388e3c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(benchmark_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("7.2 Review Entity", subheading_style))
    review_text = """
    Review entities store evaluation results and feedback:
    """
    elements.append(Paragraph(review_text, styles['Normal']))
    elements.append(Paragraph("• Review ID: Unique identifier", styles['Normal']))
    elements.append(Paragraph("• Case ID: Associated benchmark case", styles['Normal']))
    elements.append(Paragraph("• Results: Evaluation metrics (precision, recall, F1)", styles['Normal']))
    elements.append(Paragraph("• Feedback: Human feedback and corrections", styles['Normal']))
    elements.append(Paragraph("• Timestamp: When review was created", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # 8. Relationships Summary
    elements.append(Paragraph("8. Relationships Summary", heading_style))
    
    elements.append(Paragraph("<b>Core Relationships:</b>", styles['Normal']))
    elements.append(Paragraph("• documents ↔ doc_hashes: Documents tracked by hash for deduplication", styles['Normal']))
    elements.append(Paragraph("• ThreatNode ↔ ThreatEdge: Nodes connected by edges in knowledge graph", styles['Normal']))
    elements.append(Paragraph("• ATTACKTechnique ↔ ATTACKTactic: Techniques belong to tactics", styles['Normal']))
    elements.append(Paragraph("• ATTACKProcedure → ATTACKTechnique: Procedures implement techniques", styles['Normal']))
    elements.append(Paragraph("• CVE ↔ CWE: CVEs are associated with CWEs", styles['Normal']))
    elements.append(Paragraph("• CVE → ATTACKTechnique: CVEs can be exploited via techniques", styles['Normal']))
    elements.append(Paragraph("• CWE → ATTACKTechnique: CWEs can be exploited via techniques", styles['Normal']))
    elements.append(Paragraph("• AttackPath: Composed of multiple ThreatNodes and ThreatEdges", styles['Normal']))
    elements.append(Paragraph("• Benchmark → Review: Reviews evaluate benchmark cases", styles['Normal']))
    elements.append(Paragraph("• Audit Log: Tracks access to all entities", styles['Normal']))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph("<b>Key Constraints:</b>", styles['Normal']))
    elements.append(Paragraph("• doc_hashes: Unique constraint on (doc_name, service)", styles['Normal']))
    elements.append(Paragraph("• ThreatEdge: References source_id and target_id (ThreatNode.node_id)", styles['Normal']))
    elements.append(Paragraph("• AttackPath: Contains ordered lists of node and edge IDs", styles['Normal']))
    elements.append(Paragraph("• ATTACKProcedure: References technique_id (ATTACKTechnique.technique_id)", styles['Normal']))
    elements.append(Paragraph("• CVE/CWE: Cross-references via attack_techniques list", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_text = f"""
    <i>Document generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
    <br/>
    <i>Chakravyuh RAG System - Entity Relationship Diagram</i>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    print(f"✅ ERD PDF generated successfully: {output_path}")


def create_erd_with_matplotlib(output_path):
    """Create ERD PDF using matplotlib as fallback."""
    with PdfPages(output_path) as pdf:
        fig = plt.figure(figsize=(11, 8.5))
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        # Title
        ax.text(0.5, 0.95, 'Chakravyuh RAG System', 
                ha='center', va='top', fontsize=20, weight='bold')
        ax.text(0.5, 0.90, 'Entity Relationship Diagram (ERD)', 
                ha='center', va='top', fontsize=16)
        ax.text(0.5, 0.85, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                ha='center', va='top', fontsize=10, style='italic')
        
        # Note about detailed version
        ax.text(0.5, 0.75, 'Note: This is a simplified diagram. For detailed entity', 
                ha='center', va='top', fontsize=10, color='red')
        ax.text(0.5, 0.72, 'descriptions and attributes, please install reportlab', 
                ha='center', va='top', fontsize=10, color='red')
        ax.text(0.5, 0.69, 'and regenerate: pip install reportlab', 
                ha='center', va='top', fontsize=10, color='red')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    print(f"⚠️  Basic ERD PDF generated (matplotlib fallback): {output_path}")
    print("   For detailed version, install reportlab: pip install reportlab")


def main():
    """Main function to generate ERD PDF."""
    output_dir = Path(project_root) / "data" / "knowledge" / "erd"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "chakravyuh_erd_documentation.pdf"
    
    if REPORTLAB_AVAILABLE:
        create_erd_with_reportlab(output_path)
    else:
        create_erd_with_matplotlib(output_path)
        print("\n💡 Tip: Install reportlab for a detailed ERD document:")
        print("   pip install reportlab")


if __name__ == "__main__":
    main()
