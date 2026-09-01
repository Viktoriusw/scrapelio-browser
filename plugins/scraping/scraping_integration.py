import sys
import os
import json
import time
import sqlite3
import threading
import asyncio
import aiohttp
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("Warning: 'schedule' module not available")
# Importar yaml y pandas con fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    print("[WARNING] pandas not available - CSV/Excel export functions limited")
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass
from pathlib import Path
import logging
import hashlib
import gzip
import pickle
from urllib.parse import urljoin, urlparse, parse_qs
from collections import defaultdict, deque
import queue
import weakref
import re
from bs4 import BeautifulSoup
import requests

# PySide6 imports for UI
try:
    from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                                   QTextEdit, QPushButton, QLabel, QSpinBox, 
                                   QLineEdit, QComboBox, QListWidget, QListWidgetItem,
                                   QCheckBox, QGroupBox, QScrollArea, QFrame)
    from PySide6.QtCore import Qt, QThread, pyqtSignal
    from PySide6.QtGui import QFont, QColor
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("[WARNING] PySide6 no disponible - UI no disponible")

# Enhanced ScrapingIntegration with REAL functionality
class ScrapingIntegration:
    def __init__(self):
        self.initialized = False
        self.current_html = ""
        self.current_url = ""
        self.analysis_results = {}
        self.discovery_results = []
        self.extracted_data = {}  # Store extracted data
        self.selected_elements = []  # Store selected elements
        self.metrics_data = {}
        self.plugin_results = {}
        self.cache_results = {}
        self.proxy_results = {}
        self.scheduler_results = {}
        
        # Initialize all components
        self._initialize_components()
        self.initialized = True
        print("[OK] ScrapingIntegration initialized correctly")
    
    def _initialize_components(self):
        """Initialize all components"""
        try:
            # Setup basic components
            self._setup_basic_fallbacks()
            # Setup advanced features
            self._setup_advanced_features()
            
        except Exception as e:
            print(f"[ERROR] Error initializing components: {e}")
            self._setup_basic_fallbacks()
    
    def _setup_advanced_features(self):
        """Setup advanced scraping features"""
        try:
            # Setup cleanup task
            if SCHEDULE_AVAILABLE:
                schedule.every(3600).seconds.do(self._cleanup_task)
            
            # Setup metrics collection
            if SCHEDULE_AVAILABLE:
                schedule.every(300).seconds.do(self._metrics_task)
            
            # Start background thread for scheduled tasks
            self._start_background_thread()
            
        except Exception as e:
            print(f"[WARNING] Error configuring advanced features: {e}")
    
    def _setup_basic_fallbacks(self):
        """Setup basic fallback implementations"""
        self.config_manager = FallbackConfigManager()
        self.ethical_scraper = FallbackScraper()
        self.html_analyzer = FallbackAnalyzer()
        self.structured_extractor = FallbackExtractor()
        self.advanced_selectors = FallbackSelectors()
        self.intelligent_crawler = FallbackCrawler()
        self.metrics_collector = FallbackMetrics()
        self.plugin_manager = FallbackPluginManager()
        self.etl_pipeline = FallbackETL()
        self.task_scheduler = FallbackScheduler()
        self.cache_manager = FallbackCache()
        self.proxy_manager = FallbackProxyManager()
        self.user_agent_manager = FallbackUserAgentManager()
    
    def _start_background_thread(self):
        """Start background thread for scheduled tasks"""
        def run_scheduler():
            while True:
                try:
                    if SCHEDULE_AVAILABLE:
                        schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    print(f"Error in scheduler: {e}")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def _cleanup_task(self):
        """Cleanup task for maintenance"""
        try:
            # Clean old cache entries
            if hasattr(self, 'cache_manager'):
                self.cache_manager.cleanup()
        except Exception as e:
            print(f"Error in cleanup: {e}")
    
    def _metrics_task(self):
        """Metrics collection task"""
        try:
            if hasattr(self, 'metrics_collector'):
                self.metrics_collector.record_operation("scheduled_metrics", True)
        except Exception as e:
            print(f"Error in metrics: {e}")
    
    def update_content(self, html_content: str, url: str = "") -> bool:
        """Update current page content for analysis"""
        try:
            self.current_html = html_content
            self.current_url = url
            print(f"Content updated: {len(html_content)} characters from {url}")
            return True
        except Exception as e:
            print(f"Error updating content: {e}")
            return False
    
    def analyze_page(self) -> Dict[str, Any]:
        """Analyze current page HTML with REAL functionality"""
        try:
            if not self.current_html:
                return {"error": "No HTML content to analyze"}
            
            # Get proxy for this analysis if available
            current_proxy = None
            if hasattr(self, 'proxy_manager') and self.proxy_manager:
                current_proxy = self.proxy_manager.get_proxy()
                if current_proxy:
                    print(f"🔄 Using proxy: {current_proxy.url}")
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(self.current_html, 'html.parser')
            
            # Real analysis
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "url": self.current_url,
                "analysis": {
                    "links": [],
                    "images": [],
                    "forms": [],
                    "tables": [],
                    "lists": [],
                    "headings": [],
                    "paragraphs": [],
                    "buttons": [],
                    "inputs": []
                }
            }
            
            # Extract links
            for link in soup.find_all('a', href=True):
                analysis["analysis"]["links"].append({
                    "text": link.get_text(strip=True),
                    "href": link['href'],
                    "title": link.get('title', ''),
                    "class": link.get('class', [])
                })
            
            # Extract images
            for img in soup.find_all('img'):
                analysis["analysis"]["images"].append({
                    "src": img.get('src', ''),
                    "alt": img.get('alt', ''),
                    "title": img.get('title', ''),
                    "class": img.get('class', [])
                })
            
            # Extract forms
            for form in soup.find_all('form'):
                analysis["analysis"]["forms"].append({
                    "action": form.get('action', ''),
                    "method": form.get('method', 'get'),
                    "id": form.get('id', ''),
                    "class": form.get('class', [])
                })
            
            # Extract tables
            for table in soup.find_all('table'):
                analysis["analysis"]["tables"].append({
                    "id": table.get('id', ''),
                    "class": table.get('class', []),
                    "rows": len(table.find_all('tr')),
                    "headers": [th.get_text(strip=True) for th in table.find_all('th')]
                })
            
            # Extract lists
            for ul in soup.find_all(['ul', 'ol']):
                analysis["analysis"]["lists"].append({
                    "type": ul.name,
                    "id": ul.get('id', ''),
                    "class": ul.get('class', []),
                    "items": len(ul.find_all('li'))
                })
            
            # Extract headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                analysis["analysis"]["headings"].append({
                    "level": heading.name,
                    "text": heading.get_text(strip=True),
                    "id": heading.get('id', ''),
                    "class": heading.get('class', [])
                })
            
            # Extract paragraphs
            for p in soup.find_all('p'):
                analysis["analysis"]["paragraphs"].append({
                    "text": p.get_text(strip=True)[:100] + "..." if len(p.get_text(strip=True)) > 100 else p.get_text(strip=True),
                    "id": p.get('id', ''),
                    "class": p.get('class', [])
                })
            
            # Extract buttons
            for button in soup.find_all('button'):
                analysis["analysis"]["buttons"].append({
                    "text": button.get_text(strip=True),
                    "type": button.get('type', ''),
                    "id": button.get('id', ''),
                    "class": button.get('class', [])
                })
            
            # Extract inputs
            for input_elem in soup.find_all('input'):
                analysis["analysis"]["inputs"].append({
                    "type": input_elem.get('type', ''),
                    "name": input_elem.get('name', ''),
                    "id": input_elem.get('id', ''),
                    "class": input_elem.get('class', [])
                })
            
            self.analysis_results = analysis
            return analysis
            
        except Exception as e:
            return {"error": f"Error analyzing page: {str(e)}"}
    
    def discover_urls(self, max_urls: int = 100, max_depth: int = 3) -> Dict[str, Any]:
        """Discover URLs from current page with REAL functionality"""
        try:
            if not self.current_html:
                return {"error": "No HTML content to analyze"}
            
            soup = BeautifulSoup(self.current_html, 'html.parser')
            discovered_urls = []
            fuzzing_results = []
            
            # Extract all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    discovered_urls.append(href)
                elif href.startswith('/'):
                    # Convert relative to absolute
                    if self.current_url:
                        base_url = self.current_url.rstrip('/')
                        discovered_urls.append(f"{base_url}{href}")
                elif href.startswith('#'):
                    # Skip anchors
                    continue
                else:
                    # Other relative URLs
                    if self.current_url:
                        discovered_urls.append(urljoin(self.current_url, href))
            
            # Remove duplicates
            discovered_urls = list(set(discovered_urls))
            
            # Limit results
            discovered_urls = discovered_urls[:max_urls]
            
            # Generate fuzzing URLs
            if self.current_url:
                base_url = self.current_url.rstrip('/')
                common_paths = ['/admin', '/login', '/register', '/api', '/docs', '/help', '/about', '/contact']
                for path in common_paths:
                    fuzzing_results.append(f"{base_url}{path}")
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "discovered_urls": discovered_urls,
                "fuzzing_results": fuzzing_results,
                "total_discovered": len(discovered_urls),
                "total_fuzzing": len(fuzzing_results)
            }
            
            self.discovery_results = result
            return result
            
        except Exception as e:
            return {"error": f"Error discovering URLs: {str(e)}"}
    
    def extract_data(self, selectors: List[str] = None, base_url: str = None, target_attr: str = "text") -> Dict[str, Any]:
        """Extract data with configurable target attribute"""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        html = self.current_html or ""
        soup = BeautifulSoup(html, "html.parser")
        extracted = {}
        seen = set()

        for sel in selectors or []:
            items = []
            for el in soup.select(sel):
                # Extract target attribute value
                target_value = self._extract_target_attribute(el, target_attr)
                
                # Extract all common attributes
                text = " ".join(el.get_text(strip=True).split())
                href = el.get("href")
                src = el.get("src")
                alt = el.get("alt")
                title = el.get("title")
                
                data = {
                    "selector": sel,
                    "text": text,
                    "html": str(el),
                    "href": urljoin(base_url, href) if base_url and href else href,
                    "src": urljoin(base_url, src) if base_url and src else src,
                    "alt": alt,
                    "title": title,
                    "tag": getattr(el, "name", None),
                    target_attr: target_value  # Add the target attribute
                }
                
                # Create unique key for deduplication
                key = (sel, data["text"], data["href"], data["src"], target_value)
                if key in seen:
                    continue
                seen.add(key)
                items.append(data)
            extracted[sel] = items

        total = sum(len(v) for v in extracted.values())
        return {"ok": True, "total_elements": total, "extracted": extracted, "target_attr": target_attr}
    
    def _extract_target_attribute(self, element, target_attr: str):
        """Extract the target attribute value from an element"""
        try:
            if target_attr == "text":
                return " ".join(element.get_text(strip=True).split())
            elif target_attr == "innerHTML":
                return str(element)
            elif target_attr == "outerHTML":
                return str(element)
            elif target_attr == "href":
                return element.get("href", "")
            elif target_attr == "src":
                return element.get("src", "")
            elif target_attr == "alt":
                return element.get("alt", "")
            elif target_attr == "title":
                return element.get("title", "")
            elif target_attr.startswith("data-"):
                return element.get(target_attr, "")
            else:
                # Try to get as attribute
                return element.get(target_attr, "")
        except Exception as e:
            print(f"[DEBUG] Error extracting attribute {target_attr}: {e}")
            return ""
    
    def get_selectable_elements(self) -> List[Dict[str, Any]]:
        """Get all selectable elements from current page with better suggestions"""
        try:
            if not self.current_html:
                return []
            
            soup = BeautifulSoup(self.current_html, 'html.parser')
            elements = []
            
            # Priority elements that are most likely to be selected
            priority_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # Headers
                'a[href]',  # Links
                'button', 'input[type="button"]', 'input[type="submit"]',  # Buttons
                'img[alt]',  # Images with alt text
                'p',  # Paragraphs
                'span', 'div',  # General containers
                'li',  # List items
                'td', 'th',  # Table cells
                'label',  # Form labels
                'strong', 'b', 'em', 'i',  # Text emphasis
                'blockquote',  # Quotes
                'code', 'pre'  # Code blocks
            ]
            
            for selector in priority_selectors:
                for tag in soup.select(selector):
                    text = tag.get_text(strip=True)
                    if text and len(text) > 2:  # Shorter minimum for more suggestions
                        # Calculate importance score
                        importance = self._calculate_importance(tag, text)
                        
                        # Extract structured data
                        structured_data = self._extract_structured_data(tag)
                        
                        element = {
                            "tag": tag.name,
                            "text": self._clean_text(text)[:80] + "..." if len(self._clean_text(text)) > 80 else self._clean_text(text),
                            "full_text": self._clean_text(text),
                            "texto_limpio": structured_data["texto_limpio"],
                            "texto_original": structured_data["texto_original"],
                            "selector": self._generate_selector(tag),
                            "attributes": dict(tag.attrs),
                            "html": str(tag)[:150] + "..." if len(str(tag)) > 150 else str(tag),
                            "importance": importance,
                            "type": self._get_element_type(tag),
                            "structured_data": structured_data
                        }
                        elements.append(element)
            
            # Sort by importance and remove duplicates
            seen_selectors = set()
            unique_elements = []
            for element in sorted(elements, key=lambda x: x['importance'], reverse=True):
                if element['selector'] not in seen_selectors:
                    unique_elements.append(element)
                    seen_selectors.add(element['selector'])
            
            return unique_elements[:50]  # Limit to top 50 elements
            
        except Exception as e:
            print(f"Error getting selectable elements: {e}")
            return []
    
    def _calculate_importance(self, tag, text: str) -> int:
        """Calculate importance score for an element"""
        score = 0
        
        # Base score by tag type
        tag_scores = {
            'h1': 100, 'h2': 90, 'h3': 80, 'h4': 70, 'h5': 60, 'h6': 50,
            'a': 85, 'button': 80, 'input': 75,
            'img': 70, 'p': 65, 'span': 40, 'div': 35,
            'li': 60, 'td': 55, 'th': 60,
            'strong': 70, 'b': 65, 'em': 65, 'i': 60,
            'blockquote': 75, 'code': 70, 'pre': 75
        }
        
        score += tag_scores.get(tag.name, 30)
        
        # Bonus for meaningful text length
        if 10 <= len(text) <= 200:
            score += 20
        elif len(text) > 200:
            score += 10
        
        # Bonus for having href (links)
        if tag.name == 'a' and tag.get('href'):
            score += 15
        
        # Bonus for having alt text (images)
        if tag.name == 'img' and tag.get('alt'):
            score += 10
        
        # Bonus for having id or class
        if tag.get('id'):
            score += 25
        if tag.get('class'):
            score += 15
        
        return score
    
    def _get_element_type(self, tag) -> str:
        """Get human-readable element type"""
        if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return "Header"
        elif tag.name == 'a':
            return "Link"
        elif tag.name in ['button', 'input']:
            return "Button"
        elif tag.name == 'img':
            return "Image"
        elif tag.name == 'p':
            return "Paragraph"
        elif tag.name in ['span', 'div']:
            return "Container"
        elif tag.name in ['li', 'td', 'th']:
            return "List item"
        elif tag.name in ['strong', 'b', 'em', 'i']:
            return "Text emphasis"
        elif tag.name in ['blockquote', 'code', 'pre']:
            return "Quote/Code"
        else:
            return "Other"
    
    def _clean_text(self, text: str) -> str:
        """Clean and format text for better readability"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove common HTML entities
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™',
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–',
            '&lsquo;': ''',
            '&rsquo;': ''',
            '&ldquo;': '"',
            '&rdquo;': '"'
        }
        
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Limit length for display
        if len(text) > 200:
            text = text[:197] + "..."
        
        return text.strip()
    
    def _format_for_export(self, text: str) -> str:
        """Format text specifically for export (CSV, Excel, etc.)"""
        if not text:
            return ""
        
        # Clean the text first
        text = self._clean_text(text)
        
        # Remove problematic characters for CSV
        text = text.replace('"', '""')  # Escape quotes for CSV
        text = text.replace('\n', ' ')  # Replace newlines with spaces
        text = text.replace('\r', ' ')  # Replace carriage returns
        text = text.replace('\t', ' ')  # Replace tabs
        
        # Remove other problematic characters
        text = ''.join(char for char in text if char.isprintable() or char in ' \n\t')
        
        return text.strip()
    
    def _extract_structured_data(self, element) -> dict:
        """Extract structured data from an element"""
        data = {
            "texto_limpio": self._clean_text(element.get_text(strip=True)),
            "texto_original": element.get_text(strip=True),
            "tipo_elemento": element.name,
            "selector": self._generate_selector(element),
            "atributos": {}
        }
        
        # Extract useful attributes
        for attr, value in element.attrs.items():
            if attr in ['href', 'src', 'alt', 'title', 'id', 'class']:
                if isinstance(value, list):
                    data["atributos"][attr] = ' '.join(value)
                else:
                    data["atributos"][attr] = str(value)
        
        # Extract specific data based on element type
        if element.name == 'a':
            data["url"] = element.get('href', '')
            data["texto_enlace"] = self._clean_text(element.get_text(strip=True))
        elif element.name == 'img':
            data["url_imagen"] = element.get('src', '')
            data["texto_alternativo"] = element.get('alt', '')
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            data["nivel_encabezado"] = element.name
            data["texto_encabezado"] = self._clean_text(element.get_text(strip=True))
        elif element.name in ['button', 'input']:
            data["tipo_boton"] = element.get('type', 'button')
            data["valor_boton"] = element.get('value', '')
        
        return data
    
    def _generate_selector(self, element) -> str:
        """Generate robust CSS selector for an element with proper escaping and nth-of-type support"""
        try:
            if not element or not hasattr(element, 'name'):
                return "unknown"
            
            # Build selector path from root to element
            path_parts = []
            current = element
            
            while current and hasattr(current, 'name') and current.name not in ['html', 'body']:
                selector_part = self._build_selector_part(current)
                path_parts.insert(0, selector_part)
                current = current.parent
            
            # Join with child combinator
            full_selector = " > ".join(path_parts)
            
            # If we have an ID, use it as the most specific selector
            if hasattr(element, 'get') and element.get('id'):
                return f"#{self._css_escape(element['id'])}"
            
            return full_selector if full_selector else element.name
            
        except Exception as e:
            print(f"[DEBUG] Error generating selector: {e}")
            return getattr(element, 'name', 'unknown')
    
    def _build_selector_part(self, element) -> str:
        """Build a single part of the CSS selector for an element"""
        try:
            if not element or not hasattr(element, 'name'):
                return "unknown"
            
            tag = element.name
            selector = tag
            
            # Add ID if present (most specific)
            if hasattr(element, 'get') and element.get('id'):
                return f"{tag}#{self._css_escape(element['id'])}"
            
            # Add classes if present
            classes = element.get('class', []) if hasattr(element, 'get') else []
            if classes:
                escaped_classes = [self._css_escape(cls) for cls in classes[:3]]  # Limit to 3 classes
                selector += "." + ".".join(escaped_classes)
            
            # Add nth-of-type if there are siblings of the same type
            if hasattr(element, 'parent') and element.parent:
                siblings = [sib for sib in element.parent.children 
                           if hasattr(sib, 'name') and sib.name == tag]
                
                if len(siblings) > 1:
                    # Find position among siblings of same type
                    position = 1
                    for sibling in siblings:
                        if sibling is element:
                            break
                        position += 1
                    
                    selector += f":nth-of-type({position})"
            
            return selector
            
        except Exception as e:
            print(f"[DEBUG] Error building selector part: {e}")
            return getattr(element, 'name', 'unknown')
    
    def _css_escape(self, value: str) -> str:
        """Escape CSS identifiers for safe use in selectors"""
        if not value:
            return ""
        
        # Escape special characters in CSS identifiers
        import re
        # Escape characters that need escaping in CSS
        escaped = re.sub(r'([ !"#$%&\'()*+,./:;<=>?@[\\]^`{|}~])', r'\\\1', str(value))
        return escaped
    
    def add_selected_element(self, element_data: Dict[str, Any]):
        """Add element to selected elements list"""
        if element_data not in self.selected_elements:
            self.selected_elements.append(element_data)
            print(f"[OK] Element added: {element_data.get('tag', 'unknown')} - {element_data.get('text', '')[:50]}...")
    
    def add_element_by_selector(self, selector: str) -> Dict[str, Any]:
        """Add element by CSS selector from current page with pattern detection integration"""
        try:
            if not self.current_html:
                return {"error": "No HTML content to analyze"}
            
            # Try to get recommended selector from pattern detector if available
            best_selector = self._get_best_selector(selector)
            
            soup = BeautifulSoup(self.current_html, 'html.parser')
            elements = soup.select(best_selector)
            
            if not elements:
                return {"error": f"No elements found with selector: {best_selector}"}
            
            added_elements = []
            for element in elements:
                text = element.get_text(strip=True)
                if text:
                    element_data = {
                        "tag": element.name,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "full_text": text,
                        "selector": best_selector,
                        "original_selector": selector,
                        "attributes": dict(element.attrs),
                        "html": str(element)[:200] + "..." if len(str(element)) > 200 else str(element)
                    }
                    self.add_selected_element(element_data)
                    added_elements.append(element_data)
            
            return {
                "success": True,
                "elements_added": len(added_elements),
                "selector": best_selector,
                "original_selector": selector,
                "pattern_enhanced": best_selector != selector
            }
            
        except Exception as e:
            return {"error": f"Error adding elements: {str(e)}"}
    
    def _get_best_selector(self, input_selector: str) -> str:
        """Get the best selector using pattern detection if available"""
        try:
            # If pattern detector is available, try to get recommended selector
            if hasattr(self, 'detect_dom_patterns'):
                patterns_result = self.detect_dom_patterns()
                if "error" not in patterns_result and patterns_result.get("patterns"):
                    patterns = patterns_result["patterns"]
                    
                    # Look for patterns that might match the input selector
                    for pattern in patterns:
                        selectors = pattern.get("selectors", {})
                        recommended = selectors.get("recommended", "")
                        
                        if recommended and self._selector_matches_pattern(input_selector, recommended):
                            print(f"[DEBUG] Using recommended selector from pattern: {recommended}")
                            return recommended
                    
                    # If no specific match, use the first recommended selector
                    for pattern in patterns:
                        selectors = pattern.get("selectors", {})
                        recommended = selectors.get("recommended", "")
                        if recommended:
                            print(f"[DEBUG] Using first recommended selector: {recommended}")
                            return recommended
            
            # Fallback to input selector
            return input_selector
            
        except Exception as e:
            print(f"[DEBUG] Error getting best selector: {e}")
            return input_selector
    
    def _selector_matches_pattern(self, input_selector: str, recommended_selector: str) -> bool:
        """Check if input selector matches the pattern of recommended selector"""
        try:
            # Simple matching: if the input selector is a substring of recommended or vice versa
            return (input_selector in recommended_selector or 
                    recommended_selector in input_selector or
                    input_selector.split()[-1] == recommended_selector.split()[-1])
        except:
            return False
    
    def add_element_by_click(self, x: int, y: int) -> Dict[str, Any]:
        """Add element by click coordinates (simulated)"""
        try:
            if not self.current_html:
                return {"error": "No HTML content to analyze"}
            
            # This would be called from JavaScript in the browser
            # For now, we'll simulate finding elements near the click
            soup = BeautifulSoup(self.current_html, 'html.parser')
            
            # Find elements that might be at the click position
            # This is a simplified approach - in a real implementation,
            # you'd use JavaScript to get the exact element at coordinates
            clickable_elements = soup.find_all(['a', 'button', 'input', 'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            if not clickable_elements:
                return {"error": "No clickable elements found"}
            
            # For demonstration, we'll add the first few elements
            added_elements = []
            for element in clickable_elements[:3]:  # Limit to first 3 elements
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    element_data = {
                        "tag": element.name,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "full_text": text,
                        "selector": self._generate_selector(element),
                        "attributes": dict(element.attrs),
                        "html": str(element)[:200] + "..." if len(str(element)) > 200 else str(element),
                        "click_position": {"x": x, "y": y}
                    }
                    self.add_selected_element(element_data)
                    added_elements.append(element_data)
            
            return {
                "success": True,
                "elements_added": len(added_elements),
                "click_position": {"x": x, "y": y}
            }
            
        except Exception as e:
            return {"error": f"Error adding elements by click: {str(e)}"}
    
    def remove_selected_element(self, element_data: Dict[str, Any]):
        """Remove element from selected elements list"""
        if element_data in self.selected_elements:
            self.selected_elements.remove(element_data)
    
    def get_selected_elements(self) -> List[Dict[str, Any]]:
        """Get all selected elements"""
        return self.selected_elements
    
    def clear_selected_elements(self):
        """Clear all selected elements"""
        self.selected_elements.clear()
    
    def export_selected_data(self, format_type: str = "json", filename: str = None) -> Dict[str, Any]:
        """Export selected elements data with improved formatting"""
        try:
            if not self.selected_elements:
                return {"error": "No elements selected for export"}
            
            if not filename:
                filename = f"scraped_data_{int(time.time())}"
            
            # Prepare clean data for export
            clean_elements = []
            for element in self.selected_elements:
                clean_element = {
                    "tipo_elemento": element.get("tag", ""),
                    "tipo_categoria": element.get("type", ""),
                    "texto_limpio": element.get("texto_limpio", ""),
                    "texto_original": element.get("texto_original", ""),
                    "selector_css": element.get("selector", ""),
                    "importancia": element.get("importance", 0),
                    "url_pagina": self.current_url,
                    "timestamp_extraccion": datetime.now().isoformat()
                }
                
                # Add structured data if available
                if "structured_data" in element:
                    structured = element["structured_data"]
                    clean_element.update({
                        "url_enlace": structured.get("url", ""),
                        "texto_enlace": structured.get("texto_enlace", ""),
                        "url_imagen": structured.get("url_imagen", ""),
                        "texto_alternativo": structured.get("texto_alternativo", ""),
                        "nivel_encabezado": structured.get("nivel_encabezado", ""),
                        "texto_encabezado": structured.get("texto_encabezado", ""),
                        "tipo_boton": structured.get("tipo_boton", ""),
                        "valor_boton": structured.get("valor_boton", "")
                    })
                
                # Add attributes as separate columns
                attributes = element.get("attributes", {})
                for attr, value in attributes.items():
                    if attr in ['href', 'src', 'alt', 'title', 'id', 'class']:
                        clean_element[f"atributo_{attr}"] = str(value)
                
                clean_elements.append(clean_element)
            
            data_to_export = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "url": self.current_url,
                    "total_elementos": len(self.selected_elements),
                    "formato_exportacion": format_type
                },
                "elementos": clean_elements
            }
            
            if format_type == "json":
                filepath = f"{filename}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_to_export, f, indent=2, ensure_ascii=False)
            
            elif format_type == "csv":
                filepath = f"{filename}.csv"
                
                if not clean_elements:
                    return {"error": "No elements to export"}
                
                if PANDAS_AVAILABLE:
                    # Use pandas for better CSV handling
                    df = pd.DataFrame(clean_elements)
                    
                    # Reorder columns for better readability
                    priority_columns = [
                        'tipo_elemento', 'tipo_categoria', 'texto_limpio', 'texto_original',
                        'selector_css', 'importancia', 'url_enlace', 'texto_enlace',
                        'url_imagen', 'texto_alternativo', 'nivel_encabezado', 'texto_encabezado',
                        'tipo_boton', 'valor_boton'
                    ]
                    
                    # Add attribute columns
                    for col in df.columns:
                        if col.startswith('atributo_'):
                            priority_columns.append(col)
                    
                    # Reorder columns
                    existing_columns = [col for col in priority_columns if col in df.columns]
                    remaining_columns = [col for col in df.columns if col not in priority_columns]
                    final_columns = existing_columns + remaining_columns
                    
                    df = df[final_columns]
                    df.to_csv(filepath, index=False, encoding='utf-8-sig')  # UTF-8 with BOM for Excel
                else:
                    # Fallback: manual CSV creation without pandas
                    import csv
                    
                    # Get all unique keys from all elements
                    all_keys = set()
                    for element in clean_elements:
                        all_keys.update(element.keys())
                    
                    # Order keys for better readability
                    priority_keys = [
                        'tipo_elemento', 'tipo_categoria', 'texto_limpio', 'texto_original',
                        'selector_css', 'importancia', 'url_enlace', 'texto_enlace',
                        'url_imagen', 'texto_alternativo', 'nivel_encabezado', 'texto_encabezado',
                        'tipo_boton', 'valor_boton'
                    ]
                    
                    # Add remaining keys
                    remaining_keys = sorted([k for k in all_keys if k not in priority_keys])
                    ordered_keys = [k for k in priority_keys if k in all_keys] + remaining_keys
                    
                    with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=ordered_keys)
                        writer.writeheader()
                        
                        for element in clean_elements:
                            # Clean values for CSV
                            clean_row = {}
                            for key, value in element.items():
                                if isinstance(value, (list, dict)):
                                    clean_row[key] = str(value)
                                else:
                                    clean_row[key] = str(value) if value is not None else ""
                            writer.writerow(clean_row)
            
            elif format_type == "yaml":
                filepath = f"{filename}.yaml"
                if not YAML_AVAILABLE:
                    return {"error": "PyYAML not available for YAML export"}
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(data_to_export, f, default_flow_style=False, allow_unicode=True)
            
            elif format_type == "excel":
                filepath = f"{filename}.xlsx"
                if not PANDAS_AVAILABLE:
                    return {"error": "pandas not available for Excel export"}
                df = pd.DataFrame(clean_elements)
                
                # Create Excel writer with formatting
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Datos_Extraidos', index=False)
                    
                    # Get the workbook and worksheet
                    workbook = writer.book
                    worksheet = writer.sheets['Datos_Extraidos']
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return {
                "success": True,
                "format": format_type,
                "filename": filepath,
                "elements_exported": len(self.selected_elements),
                "columns_exported": len(clean_elements[0]) if clean_elements else 0
            }
            
        except Exception as e:
            return {"error": f"Error exporting data: {str(e)}"}
    
    # Keep existing methods for compatibility
    def run_plugins(self) -> Dict[str, Any]:
        """Run plugins (placeholder)"""
        return {
            "plugins_executed": 0,
            "total_plugins": 0,
            "plugin_results": {}
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "operation_stats": {
                "analyses": 1,
                "extractions": 1,
                "exports": 0
            }
        }
    
    def manage_cache(self, action: str = "info") -> Dict[str, Any]:
        """Manage cache"""
        return {
            "operation_success": True,
            "cache_info": {
                "size": 0,
                "entries": 0
            }
        }
    
    def manage_proxies(self, action: str = "info") -> Dict[str, Any]:
        """Manage proxies"""
        try:
            if not hasattr(self, 'proxy_manager') or not self.proxy_manager:
                return {
                    "operation_success": False,
                    "error": "Proxy manager not available"
                }
            
            if action == "info":
                # Get proxy statistics
                total_proxies = len(self.proxy_manager.proxies) if hasattr(self.proxy_manager, 'proxies') else 0
                active_proxies = len([p for p in self.proxy_manager.proxies if p.is_active]) if hasattr(self.proxy_manager, 'proxies') else 0
                
                return {
                    "operation_success": True,
                    "proxy_info": {
                        "total": total_proxies,
                        "active": active_proxies,
                        "enabled": getattr(self.proxy_manager, 'enabled', False),
                        "rotation_strategy": getattr(self.proxy_manager, 'rotation_strategy', 'round_robin')
                    }
                }
            elif action == "get_current":
                # Get current proxy
                current_proxy = self.proxy_manager.get_proxy()
                if current_proxy:
                    return {
                        "operation_success": True,
                        "current_proxy": current_proxy.url,
                        "proxy_details": {
                            "host": current_proxy.host,
                            "port": current_proxy.port,
                            "protocol": current_proxy.protocol,
                            "is_active": current_proxy.is_active,
                            "failure_count": current_proxy.failure_count
                        }
                    }
                else:
                    return {
                        "operation_success": False,
                        "error": "No proxies available"
                    }
            else:
                return {
                    "operation_success": False,
                    "error": f"Unrecognized action: {action}"
                }
                
        except Exception as e:
            return {
                "operation_success": False,
                "error": f"Error managing proxies: {str(e)}"
            }
    
    def manage_scheduler(self, action: str = "info") -> Dict[str, Any]:
        """Manage scheduler"""
        return {
            "operation_success": True,
            "scheduler_info": {
                "tasks": 0,
                "running": 0
            }
        }
    
    def export_data(self, format_type: str = "json", filename: str = None) -> Dict[str, Any]:
        """Export data"""
        return self.export_selected_data(format_type, filename)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                "scrapelillo_available": False,  # Scrapelillo is independent of the browser
                "components": {
                    "config_manager": hasattr(self, 'config_manager'),
                    "ethical_scraper": hasattr(self, 'ethical_scraper'),
                    "html_analyzer": hasattr(self, 'html_analyzer'),
                    "structured_extractor": hasattr(self, 'structured_extractor'),
                    "advanced_selectors": hasattr(self, 'advanced_selectors'),
                    "intelligent_crawler": hasattr(self, 'intelligent_crawler'),
                    "metrics_collector": hasattr(self, 'metrics_collector'),
                    "plugin_manager": hasattr(self, 'plugin_manager'),
                    "etl_pipeline": hasattr(self, 'etl_pipeline'),
                    "task_scheduler": hasattr(self, 'task_scheduler'),
                    "cache_manager": hasattr(self, 'cache_manager'),
                    "proxy_manager": hasattr(self, 'proxy_manager'),
                    "user_agent_manager": hasattr(self, 'user_agent_manager')
                },
                "current_state": {
                    "html_loaded": bool(self.current_html),
                    "url_loaded": bool(self.current_url),
                    "analysis_ready": bool(self.analysis_results),
                    "elements_selected": len(self.selected_elements),
                    "data_extracted": bool(self.extracted_data)
                }
            }
            return status
        except Exception as e:
            return {"error": f"Error getting status: {str(e)}"}
    
    # URL Export Functions
    def export_urls_to_csv(self, urls: List[str], filename: str = "discovered_urls.csv") -> Dict[str, Any]:
        """Export URLs to CSV format"""
        try:
            import pandas as pd
            
            # Create DataFrame with URLs
            df = pd.DataFrame({
                'url': urls,
                'discovered_at': datetime.now().isoformat(),
                'source': self.current_url or 'unknown'
            })
            
            # Save to CSV
            df.to_csv(filename, index=False, encoding='utf-8')
            
            return {
                "success": True,
                "filename": filename,
                "urls_exported": len(urls),
                "format": "CSV"
            }
        except Exception as e:
            return {"error": f"Error exporting to CSV: {str(e)}"}
    
    def export_urls_to_json(self, urls: List[str], filename: str = "discovered_urls.json") -> Dict[str, Any]:
        """Export URLs to JSON format"""
        try:
            data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "source_url": self.current_url or "unknown",
                    "total_urls": len(urls)
                },
                "urls": urls
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "filename": filename,
                "urls_exported": len(urls),
                "format": "JSON"
            }
        except Exception as e:
            return {"error": f"Error exporting to JSON: {str(e)}"}
    
    def export_urls_to_txt(self, urls: List[str], filename: str = "discovered_urls.txt") -> Dict[str, Any]:
        """Export URLs to plain text format"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Discovered URLs\n")
                f.write(f"# Exported: {datetime.now().isoformat()}\n")
                f.write(f"# Source: {self.current_url or 'unknown'}\n")
                f.write(f"# Total URLs: {len(urls)}\n\n")
                
                for i, url in enumerate(urls, 1):
                    f.write(f"{i}. {url}\n")
            
            return {
                "success": True,
                "filename": filename,
                "urls_exported": len(urls),
                "format": "TXT"
            }
        except Exception as e:
            return {"error": f"Error exporting to TXT: {str(e)}"}
    
    def export_urls_to_excel(self, urls: List[str], filename: str = "discovered_urls.xlsx") -> Dict[str, Any]:
        """Export URLs to Excel format"""
        try:
            import pandas as pd
            
            # Ensure filename has .xlsx extension
            if not filename.endswith('.xlsx'):
                filename = filename.replace('.excel', '.xlsx')
                if not filename.endswith('.xlsx'):
                    filename += '.xlsx'
            
            # Create DataFrame with URLs and metadata
            df = pd.DataFrame({
                'url': urls,
                'discovered_at': datetime.now().isoformat(),
                'source': self.current_url or 'unknown',
                'url_type': ['link' for _ in urls]  # Default type
            })
            
            # Save to Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='URLs', index=False)
                
                # Create metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['Total URLs', 'Source URL', 'Export Date', 'Format'],
                    'Value': [len(urls), self.current_url or 'unknown', datetime.now().isoformat(), 'Excel']
                })
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            return {
                "success": True,
                "filename": filename,
                "urls_exported": len(urls),
                "format": "Excel"
            }
        except Exception as e:
            return {"error": f"Error exporting to Excel: {str(e)}"}

# Fallback implementations
class FallbackScraper:
    def __init__(self, base_url="", **kwargs):
        self.base_url = base_url
        self.session = None
        self.user_agent = "Tellectus Scraper/1.0"
    
    def analyze_page(self, html_content):
        return {"elements": [], "structure": "basic", "status": "fallback"}

class FallbackAnalyzer:
    def __init__(self):
        self.detected_elements = []
    
    def analyze_html(self, html_content):
        return {"tables": [], "lists": [], "forms": [], "links": [], "images": []}

class FallbackExtractor:
    def __init__(self):
        pass
    
    def extract_structured_data(self, html_content):
        return {"data": [], "schema": "basic"}

class FallbackSelectors:
    def __init__(self):
        pass
    
    def find_elements(self, html_content, selector_type="all"):
        return []

class FallbackCrawler:
    def __init__(self, base_url="", **kwargs):
        self.base_url = base_url
        self.discovered_urls = []
    
    def discover_urls(self, max_urls=100, max_depth=3):
        return []

class FallbackMetrics:
    def __init__(self):
        self.stats = defaultdict(int)
    
    def record_operation(self, operation, success=True):
        self.stats[operation] += 1 if success else 0

class FallbackPluginManager:
    def __init__(self):
        self.plugins = {}
    
    def load_plugins(self):
        return []
    
    def get_plugin_info(self):
        return {"loaded": 0, "available": 0}

class FallbackScheduler:
    def __init__(self):
        self.tasks = {}
    
    def add_task(self, name, func, interval=3600):
        self.tasks[name] = {"func": func, "interval": interval}
    
    def get_tasks(self):
        return list(self.tasks.keys())

class FallbackCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value, ttl=3600):
        self.cache[key] = {"value": value, "expires": time.time() + ttl}

@dataclass
class ProxyInfo:
    """Class for proxy information"""
    url: str
    is_active: bool = True
    last_used: Optional[datetime] = None
    failure_count: int = 0
    speed: Optional[float] = None
    country: Optional[str] = None
    host: str = ""
    port: int = 0
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    
    def __post_init__(self):
        """Parse URL to extract components"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.protocol = parsed.scheme or "http"
            self.host = parsed.hostname or ""
            self.port = parsed.port or (8080 if self.protocol == "http" else 1080)
            self.username = parsed.username
            self.password = parsed.password
        except Exception as e:
            print(f"[WARNING] Error parsing proxy URL {self.url}: {e}")
    
    def __hash__(self):
        """Make the class hashable for use as a dictionary key"""
        return hash(self.url)
    
    def __eq__(self, other):
        """Equality comparison based on URL"""
        if not isinstance(other, ProxyInfo):
            return False
        return self.url == other.url

class FallbackProxyManager:
    def __init__(self):
        self.proxies: List[ProxyInfo] = []
        self.enabled = False
        self.rotation_strategy = 'round_robin'
        self.timeout = 10
        self.max_failures = 3
        self.validation_url = "http://httpbin.org/ip"
        self.current_index = 0
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rotation_count': 0,
            'last_rotation': None
        }

    def add_proxy(self, proxy_url: str):
        """Add proxy from URL string"""
        try:
            # Check if already exists
            for existing in self.proxies:
                if existing.url == proxy_url:
                    print(f"[WARNING] Proxy {proxy_url} already exists")
                    return
            
            proxy_info = ProxyInfo(url=proxy_url)
            self.proxies.append(proxy_info)
            print(f"[OK] Proxy added: {proxy_url}")
        except Exception as e:
            print(f"[ERROR] Error adding proxy {proxy_url}: {e}")

    def remove_proxy(self, proxy_url: str):
        """Remove proxy by URL"""
        try:
            self.proxies = [p for p in self.proxies if p.url != proxy_url]
            print(f"[OK] Proxy removed: {proxy_url}")
        except Exception as e:
            print(f"[ERROR] Error removing proxy {proxy_url}: {e}")

    def get_proxy(self) -> Optional[ProxyInfo]:
        """Get next proxy based on rotation strategy"""
        if not self.proxies or not self.enabled:
            return None
        
        # Filter active proxies
        active_proxies = [p for p in self.proxies if p.is_active and p.failure_count < self.max_failures]
        if not active_proxies:
            return None
        
        try:
            if self.rotation_strategy == 'round_robin':
                proxy = active_proxies[self.current_index % len(active_proxies)]
                self.current_index = (self.current_index + 1) % len(active_proxies)
            elif self.rotation_strategy == 'random':
                import random
                proxy = random.choice(active_proxies)
            elif self.rotation_strategy == 'weighted':
                # Prefer proxies with fewer failures and better speed
                weights = []
                for p in active_proxies:
                    weight = 1.0 / (p.failure_count + 1)  # Fewer failures = more weight
                    if p.speed:
                        weight *= (1000.0 / (p.speed + 1))  # Less latency = more weight
                    weights.append(weight)
                
                import random
                proxy = random.choices(active_proxies, weights=weights)[0]
            else:
                proxy = active_proxies[0]
            
            # Update statistics
            proxy.last_used = datetime.now()
            self.stats['rotation_count'] += 1
            self.stats['last_rotation'] = datetime.now().isoformat()
            
            return proxy
            
        except Exception as e:
            print(f"[ERROR] Error getting proxy: {e}")
            return active_proxies[0] if active_proxies else None

    def mark_proxy_failed(self, proxy_url: str):
        """Mark proxy as failed"""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.failure_count += 1
                if proxy.failure_count >= self.max_failures:
                    proxy.is_active = False
                    print(f"[WARNING] Proxy deactivated due to failures: {proxy_url}")
                break

    def mark_proxy_success(self, proxy_url: str, response_time: float = None):
        """Mark proxy as successful"""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.failure_count = max(0, proxy.failure_count - 1)  # Reduce failures
                if response_time:
                    proxy.speed = response_time
                proxy.is_active = True
                break

    def validate_proxy_sync(self, proxy: ProxyInfo) -> bool:
        """Validate proxy synchronously"""
        try:
            import requests
            proxies = {
                'http': proxy.url,
                'https': proxy.url
            }
            
            start_time = time.time()
            response = requests.get(
                self.validation_url,
                proxies=proxies,
                timeout=self.timeout,
                verify=False
            )
            response_time = (time.time() - start_time) * 1000  # ms
            
            if response.status_code == 200:
                self.mark_proxy_success(proxy.url, response_time)
                return True
            else:
                self.mark_proxy_failed(proxy.url)
                return False
                
        except Exception as e:
            print(f"[ERROR] Error validating proxy {proxy.url}: {e}")
            self.mark_proxy_failed(proxy.url)
            return False

    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        active_proxies = len([p for p in self.proxies if p.is_active])
        failed_proxies = len([p for p in self.proxies if not p.is_active])
        
        return {
            'total_proxies': len(self.proxies),
            'active_proxies': active_proxies,
            'failed_proxies': failed_proxies,
            'total_requests': self.stats['total_requests'],
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'rotation_count': self.stats['rotation_count'],
            'last_rotation': self.stats['last_rotation']
        }

class FallbackUserAgentManager:
    def __init__(self):
        self.user_agents = ["Tellectus/1.0"]
    
    def get_user_agent(self):
        return self.user_agents[0]

class FallbackConfigManager:
    def __init__(self):
        self.config = {
            "scraping": {"default_delay": 1.0, "timeout": 30},
            "cache": {"enabled": True, "max_size": 1000},
            "proxies": {"enabled": False},
            "discovery": {"max_urls": 1000, "max_depth": 3}
        }
    
    def get_config(self, section=None):
        if section:
            return self.config.get(section, {})
        return self.config

class FallbackETL:
    def __init__(self):
        pass
    
    def process_data(self, data):
        return data

# Integrate pattern detector
try:
    from pattern_detector import enhance_scraping_integration
    # Apply pattern detection enhancement
    scraping_integration = ScrapingIntegration()
    scraping_integration = enhance_scraping_integration(scraping_integration)
    print("[OK] Pattern detector integrated correctly")
except ImportError as e:
    print(f"[WARNING] Could not import pattern_detector: {e}")
    scraping_integration = ScrapingIntegration()
except Exception as e:
    print(f"[WARNING] Error integrating pattern detector: {e}")
    scraping_integration = ScrapingIntegration()
