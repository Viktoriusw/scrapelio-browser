#!/usr/bin/env python3
"""
Tier Manager - Controls feature access based on subscription tier

Manages FREE, PROFESSIONAL, and ENTERPRISE tier features and limitations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from PySide6.QtCore import QObject, Signal


class TierManager(QObject):
    """
    Manages tier-based feature access and usage limits
    
    Tiers:
    - FREE: Basic analysis, 10/day limit
    - PROFESSIONAL: Advanced analysis, unlimited, integrations
    - ENTERPRISE: AI features, unlimited everything
    """
    
    # Signals
    tier_upgraded = Signal(str)  # new_tier
    limit_reached = Signal(str)  # limit_type
    feature_blocked = Signal(str, str)  # feature_name, tier_required
    
    def __init__(self, current_tier: str = "FREE"):
        super().__init__()
        self.current_tier = current_tier.upper()
        
        # Usage tracking
        self.analyses_count = {}  # date -> count
        self.last_reset_date = date.today()
        
        # Tier configurations (imported from __init__.py)
        from .. import TIER_CONFIG
        self.tier_config = TIER_CONFIG
        
        print(f"[TierManager] Initialized with tier: {self.current_tier}")
    
    def get_tier(self) -> str:
        """Get current tier"""
        return self.current_tier
    
    def set_tier(self, new_tier: str):
        """
        Update user's tier
        
        Args:
            new_tier: "FREE", "PROFESSIONAL", or "ENTERPRISE"
        """
        new_tier = new_tier.upper()
        if new_tier in self.tier_config:
            old_tier = self.current_tier
            self.current_tier = new_tier
            print(f"[TierManager] Tier upgraded: {old_tier} -> {new_tier}")
            self.tier_upgraded.emit(new_tier)
        else:
            print(f"[TierManager] Invalid tier: {new_tier}")
    
    def has_feature(self, feature_name: str) -> bool:
        """
        Check if current tier has access to a feature
        
        Args:
            feature_name: Feature identifier
            
        Returns:
            bool: True if feature is available
        """
        config = self.tier_config.get(self.current_tier, {})
        features = config.get("features", [])
        return feature_name in features
    
    def can_use_feature(self, feature_name: str, show_upgrade_prompt: bool = True) -> bool:
        """
        Check if feature can be used and optionally show upgrade prompt
        
        Args:
            feature_name: Feature identifier
            show_upgrade_prompt: Whether to emit blocked signal
            
        Returns:
            bool: True if feature can be used
        """
        if self.has_feature(feature_name):
            return True
        
        # Feature not available, determine required tier
        required_tier = self._get_required_tier(feature_name)
        
        if show_upgrade_prompt:
            self.feature_blocked.emit(feature_name, required_tier)
        
        return False
    
    def _get_required_tier(self, feature_name: str) -> str:
        """Get minimum tier required for a feature"""
        for tier in ["FREE", "PROFESSIONAL", "ENTERPRISE"]:
            config = self.tier_config.get(tier, {})
            if feature_name in config.get("features", []):
                return tier
        return "ENTERPRISE"  # Default to highest tier
    
    def can_analyze_today(self) -> bool:
        """
        Check if user can perform another analysis today
        
        Returns:
            bool: True if analysis is allowed
        """
        # Reset counter if it's a new day
        today = date.today()
        if today != self.last_reset_date:
            self.analyses_count = {}
            self.last_reset_date = today
        
        # Get daily limit
        config = self.tier_config.get(self.current_tier, {})
        limit = config.get("daily_analyses_limit", 0)
        
        # -1 means unlimited
        if limit == -1:
            return True
        
        # Check current count
        today_str = str(today)
        current_count = self.analyses_count.get(today_str, 0)
        
        if current_count >= limit:
            self.limit_reached.emit("daily_analyses")
            return False
        
        return True
    
    def increment_analysis_count(self):
        """Increment today's analysis count"""
        today = date.today()
        today_str = str(today)
        
        self.analyses_count[today_str] = self.analyses_count.get(today_str, 0) + 1
        
        print(f"[TierManager] Analyses today: {self.analyses_count[today_str]}")
    
    def get_remaining_analyses(self) -> int:
        """
        Get remaining analyses for today
        
        Returns:
            int: Number of remaining analyses (-1 for unlimited)
        """
        config = self.tier_config.get(self.current_tier, {})
        limit = config.get("daily_analyses_limit", 0)
        
        if limit == -1:
            return -1  # Unlimited
        
        today = date.today()
        today_str = str(today)
        current_count = self.analyses_count.get(today_str, 0)
        
        return max(0, limit - current_count)
    
    def get_tier_info(self) -> Dict[str, Any]:
        """
        Get complete information about current tier
        
        Returns:
            dict: Tier configuration and usage stats
        """
        config = self.tier_config.get(self.current_tier, {})
        
        return {
            "tier": self.current_tier,
            "name": config.get("name", "Unknown"),
            "daily_limit": config.get("daily_analyses_limit", 0),
            "remaining_today": self.get_remaining_analyses(),
            "features": config.get("features", []),
            "max_competitors": config.get("max_competitors", 0),
            "max_keywords": config.get("max_tracked_keywords", 0),
            "ai_features": config.get("ai_features", False),
            "api_integrations": config.get("api_integrations", False),
            "crawler_max_urls": config.get("crawler_max_urls", 0),
            "priority_support": config.get("priority_support", False),
            "price": config.get("price", 0)
        }
    
    def get_feature_list(self) -> List[str]:
        """Get list of features available in current tier"""
        config = self.tier_config.get(self.current_tier, {})
        return config.get("features", [])
    
    def compare_tiers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comparison of all tiers
        
        Returns:
            dict: Complete tier comparison
        """
        comparison = {}
        
        for tier_name in ["FREE", "PROFESSIONAL", "ENTERPRISE"]:
            config = self.tier_config.get(tier_name, {})
            comparison[tier_name] = {
                "name": config.get("name", tier_name),
                "daily_limit": config.get("daily_analyses_limit", 0),
                "features_count": len(config.get("features", [])),
                "max_competitors": config.get("max_competitors", 0),
                "max_keywords": config.get("max_tracked_keywords", 0),
                "ai_features": config.get("ai_features", False),
                "price": config.get("price", 0),
                "features": config.get("features", [])
            }
        
        return comparison
    
    def get_upgrade_benefits(self, target_tier: str) -> List[str]:
        """
        Get list of benefits from upgrading to target tier
        
        Args:
            target_tier: Target tier name
            
        Returns:
            list: List of new features user would get
        """
        target_tier = target_tier.upper()
        
        if target_tier not in self.tier_config:
            return []
        
        current_features = set(self.get_feature_list())
        target_config = self.tier_config.get(target_tier, {})
        target_features = set(target_config.get("features", []))
        
        # Get new features
        new_features = target_features - current_features
        
        return sorted(list(new_features))
    
    def is_premium(self) -> bool:
        """Check if current tier is premium (not FREE)"""
        return self.current_tier in ["PROFESSIONAL", "ENTERPRISE"]
    
    def is_enterprise(self) -> bool:
        """Check if current tier is ENTERPRISE"""
        return self.current_tier == "ENTERPRISE"
    
    def get_tier_badge_emoji(self) -> str:
        """Get emoji badge for current tier"""
        badges = {
            "FREE": "🆓",
            "PROFESSIONAL": "💼",
            "ENTERPRISE": "🏢"
        }
        return badges.get(self.current_tier, "❓")
    
    def get_tier_color(self) -> str:
        """Get color code for current tier"""
        colors = {
            "FREE": "#6c757d",  # Gray
            "PROFESSIONAL": "#007bff",  # Blue
            "ENTERPRISE": "#28a745"  # Green
        }
        return colors.get(self.current_tier, "#6c757d")
    
    def export_usage_stats(self) -> Dict[str, Any]:
        """Export usage statistics"""
        return {
            "tier": self.current_tier,
            "analyses_history": self.analyses_count,
            "last_reset": str(self.last_reset_date),
            "remaining_today": self.get_remaining_analyses()
        }
    
    def reset_daily_limit(self):
        """Manually reset daily limit (admin function)"""
        self.analyses_count = {}
        self.last_reset_date = date.today()
        print("[TierManager] Daily limit manually reset")

