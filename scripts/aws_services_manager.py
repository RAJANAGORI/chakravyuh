#!/usr/bin/env python3
"""
AWS Services Manager - Helper script to manage and optimize AWS service configurations.
"""
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_aws_services_config(config_path: Path = None) -> Dict[str, Any]:
    """Load AWS services configuration from YAML file."""
    if config_path is None:
        config_path = project_root / "config" / "aws_services.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"AWS services config not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_services_by_priority(config: Dict[str, Any], priority: str = None) -> List[Dict[str, str]]:
    """
    Get services filtered by priority.
    
    Args:
        config: AWS services configuration
        priority: Filter by priority (critical/high/medium/low), None for all
    
    Returns:
        List of service dictionaries with name and url
    """
    services = []
    
    for category, service_list in config.items():
        if isinstance(service_list, list):
            for service in service_list:
                if isinstance(service, dict):
                    if priority is None or service.get('priority') == priority:
                        services.append({
                            'name': service['name'],
                            'url': service['url'],
                            'priority': service.get('priority', 'medium'),
                            'category': category
                        })
    
    return services


def generate_config_yaml(services: List[Dict[str, str]], output_path: Path = None) -> str:
    """
    Generate config.yaml format from services list.
    
    Args:
        services: List of service dictionaries
        output_path: Optional path to write output
    
    Returns:
        YAML string in config.yaml format
    """
    yaml_content = {
        'aws_docs': {
            'base_dir': './aws_docs',
            'max_workers': 4,
            'services': [
                {'name': svc['name'], 'url': svc['url']}
                for svc in services
            ]
        }
    }
    
    yaml_str = yaml.dump(yaml_content, default_flow_style=False, sort_keys=False)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(yaml_str)
        print(f"✅ Generated config at: {output_path}")
    
    return yaml_str


def list_services(config: Dict[str, Any], by_category: bool = False):
    """List all configured services."""
    if by_category:
        for category, service_list in config.items():
            if isinstance(service_list, list):
                print(f"\n📁 {category.upper().replace('_', ' ')}")
                for service in service_list:
                    if isinstance(service, dict):
                        priority_emoji = {
                            'critical': '🔴',
                            'high': '🟠',
                            'medium': '🟡',
                            'low': '🟢'
                        }.get(service.get('priority', 'medium'), '⚪')
                        print(f"  {priority_emoji} {service['name']:20} - {service.get('priority', 'medium')}")
    else:
        services = get_services_by_priority(config)
        print(f"\n📋 All Services ({len(services)} total):\n")
        for svc in sorted(services, key=lambda x: (
            {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['priority'], 4),
            x['name']
        )):
            priority_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(svc['priority'], '⚪')
            print(f"  {priority_emoji} {svc['name']:20} [{svc['category']}]")


def update_main_config(priority_filter: str = None, dry_run: bool = False):
    """
    Update main config.yaml with services from aws_services.yaml.
    
    Args:
        priority_filter: Only include services with this priority or higher
        dry_run: If True, only print what would be updated
    """
    config = load_aws_services_config()
    
    # Priority order: critical > high > medium > low
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    
    all_services = get_services_by_priority(config)
    
    if priority_filter:
        filter_level = priority_order.get(priority_filter, 3)
        filtered_services = [
            svc for svc in all_services
            if priority_order.get(svc['priority'], 3) <= filter_level
        ]
    else:
        filtered_services = all_services
    
    # Sort by priority
    filtered_services.sort(key=lambda x: (
        priority_order.get(x['priority'], 3),
        x['name']
    ))
    
    print(f"\n📊 Services to include: {len(filtered_services)}")
    if priority_filter:
        print(f"   Filter: {priority_filter} and higher")
    
    if dry_run:
        print("\n🔍 DRY RUN - Would update config.yaml with:")
        for svc in filtered_services[:10]:  # Show first 10
            print(f"  - {svc['name']}: {svc['url']}")
        if len(filtered_services) > 10:
            print(f"  ... and {len(filtered_services) - 10} more")
    else:
        # Read existing config
        main_config_path = project_root / "config" / "config.yaml"
        if main_config_path.exists():
            with open(main_config_path, 'r') as f:
                main_config = yaml.safe_load(f)
        else:
            main_config = {}
        
        # Update aws_docs section
        if 'aws_docs' not in main_config:
            main_config['aws_docs'] = {}
        
        main_config['aws_docs']['base_dir'] = main_config['aws_docs'].get('base_dir', './aws_docs')
        main_config['aws_docs']['max_workers'] = main_config['aws_docs'].get('max_workers', 4)
        main_config['aws_docs']['services'] = [
            {'name': svc['name'], 'url': svc['url']}
            for svc in filtered_services
        ]
        
        # Write back
        with open(main_config_path, 'w') as f:
            yaml.dump(main_config, f, default_flow_style=False, sort_keys=False)
        
        print(f"\n✅ Updated {main_config_path}")
        print(f"   Added {len(filtered_services)} services")


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage AWS services configuration for documentation scraping"
    )
    parser.add_argument(
        'command',
        choices=['list', 'update', 'generate'],
        help='Command to execute'
    )
    parser.add_argument(
        '--priority',
        choices=['critical', 'high', 'medium', 'low'],
        help='Filter by priority (for update/generate)'
    )
    parser.add_argument(
        '--by-category',
        action='store_true',
        help='List services grouped by category'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path (for generate command)'
    )
    
    args = parser.parse_args()
    
    try:
        config = load_aws_services_config()
        
        if args.command == 'list':
            list_services(config, by_category=args.by_category)
        
        elif args.command == 'update':
            update_main_config(priority_filter=args.priority, dry_run=args.dry_run)
        
        elif args.command == 'generate':
            services = get_services_by_priority(config, priority=args.priority)
            if args.output:
                generate_config_yaml(services, args.output)
            else:
                print(generate_config_yaml(services))
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
