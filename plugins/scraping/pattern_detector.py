#!/usr/bin/env python3
"""
Detector de Patrones DOM - Mejora el selector visual y detecta elementos repetitivos
Similar a Panda the ultimate web scraper
"""

import re
from collections import defaultdict, Counter
from typing import List, Dict, Any, Set, Tuple
from bs4 import BeautifulSoup, Tag
import math

class DOMPatternDetector:
    def __init__(self):
        self.similarity_threshold = 0.85  # Threshold to consider similar elements
        self.min_elements_for_pattern = 2  # Minimum elements to consider a pattern
    
    def _css_escape(self, s: str) -> str:
        # FIX: simple CSS escape for ids/classes with special characters
        return re.sub(r'([ !"#$%&\'()*+,./:;<=>?@[\\]^`{|}~])', r'\\\1', s or "")
    
    def detect_patterns(self, html_content: str) -> Dict[str, Any]:
        """
        Detecta patrones repetitivos en el DOM y devuelve información sobre ellos
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            patterns = {
                "lists": self._detect_lists(soup),
                "tables": self._detect_tables(soup),
                "cards": self._detect_cards(soup),
                "repeated_elements": self._detect_repeated_elements(soup)
            }
            
            # Combinar todos los patrones detectados
            all_patterns = []
            for pattern_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    pattern["type"] = pattern_type
                    all_patterns.append(pattern)
            
            return {
                "success": True,
                "patterns": all_patterns,
                "total_patterns": len(all_patterns)
            }
        except Exception as e:
            return {"error": f"Error detecting patterns: {str(e)}"}
    
    def _detect_lists(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detects lists (ul/ol with li elements)"""
        lists = []
        for list_tag in soup.find_all(['ul', 'ol']):
            items = list_tag.find_all('li', recursive=False)
            if len(items) >= self.min_elements_for_pattern:
                # Analyze similarity between list items
                similarity_score = self._calculate_list_similarity(items)
                
                if similarity_score >= self.similarity_threshold:
                    selectors = self._generate_selectors_for_elements(items)
                    
                    lists.append({
                        "element": str(list_tag)[:200] + "..." if len(str(list_tag)) > 200 else str(list_tag),
                        "tag": list_tag.name,
                        "items_count": len(items),
                        "similarity_score": similarity_score,
                        "selectors": selectors,
                        "sample_items": [self._extract_item_info(item) for item in items[:3]]
                    })
        
        return lists
    
    def _detect_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detects tables with repetitive rows"""
        tables = []
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) >= self.min_elements_for_pattern:
                # Search for patterns in rows (excluding potential header)
                data_rows = rows[1:] if len(rows) > 2 else rows
                
                if len(data_rows) >= self.min_elements_for_pattern:
                    similarity_score = self._calculate_table_row_similarity(data_rows)
                    
                    if similarity_score >= self.similarity_threshold:
                        selectors = self._generate_selectors_for_elements(data_rows)
                        
                        tables.append({
                            "element": str(table)[:200] + "..." if len(str(table)) > 200 else str(table),
                            "tag": table.name,
                            "rows_count": len(rows),
                            "similarity_score": similarity_score,
                            "selectors": selectors,
                            "sample_rows": [self._extract_row_info(row) for row in data_rows[:2]]
                        })
        
        return tables
    
    def _detect_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detects elements of type 'card' with similar structure"""
        # Search for containers with multiple elements that have a similar structure
        containers = soup.find_all(['div', 'section', 'article'])
        cards = []
        
        for container in containers:
            # Search for direct children with the same tag
            direct_children = [child for child in container.children if isinstance(child, Tag)]
            
            if len(direct_children) >= self.min_elements_for_pattern:
                # Group by tag type
                children_by_tag = defaultdict(list)
                for child in direct_children:
                    children_by_tag[child.name].append(child)
                
                # For each group of tags, check similarity
                for tag, elements in children_by_tag.items():
                    if len(elements) >= self.min_elements_for_pattern:
                        similarity_score = self._calculate_structure_similarity(elements)
                        
                        if similarity_score >= self.similarity_threshold:
                            selectors = self._generate_selectors_for_elements(elements)
                            
                            cards.append({
                                "container": str(container)[:100] + "..." if len(str(container)) > 100 else str(container),
                                "element_tag": tag,
                                "elements_count": len(elements),
                                "similarity_score": similarity_score,
                                "selectors": selectors,
                                "sample_elements": [self._extract_element_info(elem) for elem in elements[:2]]
                            })
        
        return cards
    
    def _detect_repeated_elements(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Detects repeated elements throughout the document"""
        # Count all tags
        all_tags = soup.find_all()
        tag_counts = Counter([tag.name for tag in all_tags])
        
        repeated_elements = []
        
        # For tags that appear multiple times
        for tag, count in tag_counts.items():
            if count >= self.min_elements_for_pattern and tag not in ['html', 'body', 'head', 'meta', 'link', 'script', 'style']:
                elements = soup.find_all(tag)
                
                # Check if they have a similar structure
                similarity_score = self._calculate_structure_similarity(elements)
                
                if similarity_score >= self.similarity_threshold:
                    selectors = self._generate_selectors_for_elements(elements)
                    
                    repeated_elements.append({
                        "tag": tag,
                        "count": count,
                        "similarity_score": similarity_score,
                        "selectors": selectors,
                        "sample_elements": [self._extract_element_info(elem) for elem in elements[:2]]
                    })
        
        return repeated_elements
    
    def _calculate_list_similarity(self, items: List[Tag]) -> float:
        """Calculates similarity between list items"""
        if len(items) < 2:
            return 0.0
        
        # Compare HTML structure of elements
        structures = [self._get_element_structure(item) for item in items]
        return self._calculate_similarity_score(structures)
    
    def _calculate_table_row_similarity(self, rows: List[Tag]) -> float:
        """Calculates similarity between table rows"""
        if len(rows) < 2:
            return 0.0
        
        # Compare number of cells and structure
        cell_counts = [len(row.find_all(['td', 'th'])) for row in rows]
        
        # If all rows have the same number of cells
        if len(set(cell_counts)) == 1:
            # Compare cell structure
            structures = [self._get_element_structure(row) for row in rows]
            return self._calculate_similarity_score(structures)
        
        return 0.0
    
    def _calculate_structure_similarity(self, elements: List[Tag]) -> float:
        """Calculates structural similarity between elements"""
        if len(elements) < 2:
            return 0.0
        
        structures = [self._get_element_structure(elem) for elem in elements]
        return self._calculate_similarity_score(structures)
    
    def _get_element_structure(self, element: Tag) -> str:
        """Gets a representation of the element's structure"""
        # Simplify the structure for comparison
        structure = element.name
        
        # Add classes if they exist (only the first 2 to not make it too specific)
        classes = element.get('class', [])
        if classes and len(classes) > 0:
            structure += f".{'.'.join(classes[:2])}"
        
        # For elements with children, add structure information
        children = [child for child in element.children if isinstance(child, Tag)]
        if children:
            child_tags = Counter([child.name for child in children])
            structure += "[" + ",".join([f"{tag}:{count}" for tag, count in child_tags.items()]) + "]"
        
        return structure
    
    def _calculate_similarity_score(self, structures: List[str]) -> float:
        """Calculates a similarity score between structures"""
        if not structures:
            return 0.0
        
        # Count how many structures are identical to the first one
        first_structure = structures[0]
        matches = sum(1 for structure in structures if structure == first_structure)
        
        return matches / len(structures)
    
    def _generate_selectors_for_elements(self, elements):
        # FIX: body orientative: use previous helpers
        ca_node = self._find_common_ancestor(elements)
        common_ancestor = self._generate_css_selector(ca_node) if ca_node else ""
        common_selector = self._find_common_selector(elements)
        index_selectors = self._generate_index_selectors(common_ancestor, elements) if elements else []
        recommended = (common_selector
                       or (f"{common_ancestor} > {elements[0].name}" if common_ancestor and getattr(elements[0], "name", None) else "")
                       or (index_selectors[0] if index_selectors else ""))
        return {
            "common_ancestor": common_ancestor,
            "common_selector": common_selector,
            "index_selectors": index_selectors,
            "recommended": recommended
        }
    
    def _find_common_ancestor(self, elements):
        # FIX: compare from root (html) downwards
        def path_to_root(e):
            p, cur = [], e
            while cur is not None:
                p.append(cur)
                cur = cur.parent if hasattr(cur, "parent") else None
            return list(reversed(p))  # html ..→ e
        paths = [path_to_root(e) for e in elements if e is not None]
        if not paths:
            return None
        min_len = min(len(p) for p in paths)
        last_common = None
        for i in range(min_len):
            heads = [p[i] for p in paths]
            if all(h is heads[0] for h in heads):
                last_common = heads[0]
            else:
                break
        return last_common  # returns the node (not string)
    
    def _find_common_selector(self, elements):
        # FIX: construct by tag + intersection of classes
        if not elements:
            return ""
        first = elements[0]
        tag = first.name if getattr(first, "name", None) else ""
        if not tag:
            return ""
        common = set(first.get("class", []))
        for el in elements[1:]:
            common &= set(el.get("class", []))
        classes = sorted(list(common))[:2]
        sel = tag
        if classes:
            sel += "." + ".".join(self._css_escape(c) for c in classes)
        return sel
    
    def _generate_index_selectors(self, parent_selector: str, elements: List[Tag]) -> List[str]:
        # FIX: use nth-of-type and construct selectors relative to the same parent
        out = []
        for el in elements:
            tag = el.name
            pos = 1
            sib = el
            # count only siblings of the same type
            while (sib := sib.previous_sibling):
                if getattr(sib, "name", None) == tag:
                    pos += 1
            part = f"{tag}:nth-of-type({pos})"
            out.append(f"{parent_selector} > {part}" if parent_selector else part)
        return out
    
    def _generate_css_selector(self, el):
        # FIX: selector of THE SAME node (without spaces)
        if not el or not getattr(el, "name", None):
            return ""
        parts = [el.name]
        el_id = el.get("id")
        if el_id:
            parts.append(f"#{self._css_escape(el_id)}")
        classes = el.get("class") or []
        if classes:
            parts.append("." + ".".join(self._css_escape(c) for c in classes[:3]))
        return "".join(parts)
    
    def _extract_item_info(self, item: Tag) -> Dict[str, Any]:
        """Extracts information for an element to display as an example"""
        return {
            "text": item.get_text(strip=True)[:100] + "..." if len(item.get_text(strip=True)) > 100 else item.get_text(strip=True),
            "html": str(item)[:150] + "..." if len(str(item)) > 150 else str(item)
        }
    
    def _extract_row_info(self, row: Tag) -> Dict[str, Any]:
        """Extracts information for a table row"""
        cells = row.find_all(['td', 'th'])
        cell_texts = [cell.get_text(strip=True)[:50] + "..." if len(cell.get_text(strip=True)) > 50 else cell.get_text(strip=True) for cell in cells]
        
        return {
            "cells_count": len(cells),
            "cell_contents": cell_texts
        }
    
    def _extract_element_info(self, element: Tag) -> Dict[str, Any]:
        """Extracts generic element information"""
        return {
            "text": element.get_text(strip=True)[:100] + "..." if len(element.get_text(strip=True)) > 100 else element.get_text(strip=True),
            "html": str(element)[:150] + "..." if len(str(element)) > 150 else str(element)
        }


# Integración con el sistema existente
def enhance_scraping_integration(scraping_integration):
    """Adds pattern detection capabilities to the existing scraping integration"""
    scraping_integration.pattern_detector = DOMPatternDetector()
    
    # Add method to detect patterns
    def detect_dom_patterns(self):
        """Detects patterns in the current DOM"""
        if not self.current_html:
            return {"error": "No HTML content to analyze"}
        
        return self.pattern_detector.detect_patterns(self.current_html)
    
    # Add method to the scraping integration class
    scraping_integration.detect_dom_patterns = detect_dom_patterns.__get__(scraping_integration, type(scraping_integration))
    
    return scraping_integration

# Alias for compatibility
PatternDetector = DOMPatternDetector
