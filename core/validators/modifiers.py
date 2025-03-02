# core/validators/modifiers.py
from typing import Dict, List
from config.settings import settings

class ModifierValidator:
    def validate(self, hcfa_data: Dict) -> Dict:
        """Validate modifiers in line items"""
        invalid_modifiers = []
        
        for line in hcfa_data.get('line_items', []):
            # Check for invalid modifiers (26 or TC)
            if 'modifier' in line and line['modifier']:
                modifier = line['modifier'].upper()
                if any(inv_mod in modifier for inv_mod in settings.INVALID_MODIFIERS):
                    invalid_modifiers.append({
                        'cpt': line.get('cpt'),
                        'modifier': line['modifier']
                    })
        
        return {
            "status": "FAIL" if invalid_modifiers else "PASS",
            "invalid_modifiers": invalid_modifiers,
            "details": {
                "total_checked": len(hcfa_data.get('line_items', [])),
                "total_invalid": len(invalid_modifiers)
            }
        }