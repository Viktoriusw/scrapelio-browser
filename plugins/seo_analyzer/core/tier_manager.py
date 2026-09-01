#!/usr/bin/env python3
"""
Tier Manager
Manages feature access based on subscription tier
"""

from typing import Dict, List, Any


class TierManager:
    """Manages access to features based on subscription tier"""
    
    # Define feature access per tier
    TIER_FEATURES = {
        "free": {
            "analyzers": ["meta", "heading", "image"],
            "max_analyses_per_day": 10,
            "export_formats": ["json"],
            "history_days": 0,
            "competitor_analysis": False,
            "ai_recommendations": False,
            "api_access": False
        },
        "pro": {
            "analyzers": ["meta", "heading", "image", "link", "performance", "schema", "accessibility"],
            "max_analyses_per_day": 100,
            "export_formats": ["json", "csv", "pdf"],
            "history_days": 30,
            "competitor_analysis": False,
            "ai_recommendations": True,
            "api_access": False
        },
        "enterprise": {
            "analyzers": ["meta", "heading", "image", "link", "performance", "schema", "accessibility"],
            "max_analyses_per_day": -1,  # unlimited
            "export_formats": ["json", "csv", "pdf"],
            "history_days": 365,
            "competitor_analysis": True,
            "ai_recommendations": True,
            "api_access": True
        }
    }
    
    def __init__(self, current_tier: str = "free"):
        """
        Initialize Tier Manager
        
        Args:
            current_tier: Current subscription tier (free, pro, enterprise)
        """
        self.current_tier = current_tier.lower()
        if self.current_tier not in self.TIER_FEATURES:
            self.current_tier = "free"
    
    def set_tier(self, tier: str):
        """Set current tier"""
        tier = tier.lower()
        if tier in self.TIER_FEATURES:
            self.current_tier = tier
    
    def get_tier(self) -> str:
        """Get current tier"""
        return self.current_tier
    
    def can_use_analyzer(self, analyzer_name: str) -> bool:
        """Check if analyzer is available in current tier"""
        available_analyzers = self.TIER_FEATURES[self.current_tier]["analyzers"]
        return analyzer_name in available_analyzers
    
    def can_export_format(self, format_name: str) -> bool:
        """Check if export format is available in current tier"""
        available_formats = self.TIER_FEATURES[self.current_tier]["export_formats"]
        return format_name.lower() in available_formats
    
    def get_max_analyses_per_day(self) -> int:
        """Get maximum analyses allowed per day (-1 = unlimited)"""
        return self.TIER_FEATURES[self.current_tier]["max_analyses_per_day"]
    
    def get_history_days(self) -> int:
        """Get number of days to keep history"""
        return self.TIER_FEATURES[self.current_tier]["history_days"]
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if a specific feature is available"""
        return self.TIER_FEATURES[self.current_tier].get(feature_name, False)
    
    def get_available_analyzers(self) -> List[str]:
        """Get list of available analyzers for current tier"""
        return self.TIER_FEATURES[self.current_tier]["analyzers"]
    
    def get_available_export_formats(self) -> List[str]:
        """Get list of available export formats for current tier"""
        return self.TIER_FEATURES[self.current_tier]["export_formats"]
    
    def get_tier_info(self) -> Dict[str, Any]:
        """Get all info about current tier"""
        return {
            "tier": self.current_tier,
            "features": self.TIER_FEATURES[self.current_tier]
        }
    
    def get_upgrade_benefits(self, target_tier: str) -> Dict[str, Any]:
        """Get benefits of upgrading to target tier"""
        target_tier = target_tier.lower()
        if target_tier not in self.TIER_FEATURES or target_tier == self.current_tier:
            return {}
        
        current_features = self.TIER_FEATURES[self.current_tier]
        target_features = self.TIER_FEATURES[target_tier]
        
        benefits = {
            "new_analyzers": list(set(target_features["analyzers"]) - set(current_features["analyzers"])),
            "new_export_formats": list(set(target_features["export_formats"]) - set(current_features["export_formats"])),
            "increased_analyses": target_features["max_analyses_per_day"] - current_features["max_analyses_per_day"],
            "increased_history": target_features["history_days"] - current_features["history_days"],
            "new_features": []
        }
        
        for feature in ["competitor_analysis", "ai_recommendations", "api_access"]:
            if target_features[feature] and not current_features[feature]:
                benefits["new_features"].append(feature)
        
        return benefits
