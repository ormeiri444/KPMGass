import os
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class HealthServiceParser:
    """Parser for health service HTML files"""
    
    def __init__(self, data_directory: str):
        self.data_directory = data_directory
        self.services_data = {}
        self.load_all_services()
    
    def load_all_services(self):
        """Load all HTML service files"""
        try:
            if not os.path.exists(self.data_directory):
                logger.error(f"Data directory not found: {self.data_directory}")
                return
                
            html_files = [f for f in os.listdir(self.data_directory) if f.endswith('.html')]
            logger.info(f"Found HTML files: {html_files}")
            
            for file in html_files:
                service_type = file.replace('.html', '').replace('_services', '')
                file_path = os.path.join(self.data_directory, file)
                
                logger.info(f"Processing file: {file} -> service_type: {service_type}")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    parsed_data = self.parse_html_service(content, service_type)
                    if parsed_data:
                        self.services_data[service_type] = parsed_data
                        logger.info(f"Loaded service data for: {service_type}")
                        
                        # Log table structure for debugging
                        if parsed_data.get('benefits_table'):
                            services_list = list(parsed_data['benefits_table'].keys())
                            logger.info(f"  Services in {service_type}: {services_list}")
                
                except Exception as e:
                    logger.error(f"Error loading {file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error loading services: {e}")
    
    def parse_html_service(self, html_content: str, service_type: str) -> Dict:
        """Parse HTML content to extract service information"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = soup.find('h2')
            title_text = title.get_text().strip() if title else service_type
            
            # Extract description
            description_p = soup.find('p')
            description = description_p.get_text().strip() if description_p else ""
            
            # Extract services list
            services_list = []
            ul_elements = soup.find_all('ul')
            for ul in ul_elements:
                if ul.find_previous('p'):  # Only take lists after description
                    li_elements = ul.find_all('li')
                    for li in li_elements:
                        services_list.append(li.get_text().strip())
                    break
            
            # Extract table data
            table_data = self.extract_table_data(soup)
            
            # Extract contact information
            contact_info = self.extract_contact_info(soup)
            
            return {
                'title': title_text,
                'description': description,
                'services_list': services_list,
                'benefits_table': table_data,
                'contact_info': contact_info
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTML for {service_type}: {e}")
            return {}
    
    def extract_table_data(self, soup: BeautifulSoup) -> Dict:
        """Extract benefits table data"""
        table_data = {}
        
        try:
            table = soup.find('table')
            if not table:
                return table_data
            
            rows = table.find_all('tr')
            if len(rows) < 2:
                return table_data
            
            # Extract headers (should be: שם השירות, מכבי, מאוחדת, כללית)
            headers = [th.get_text().strip() for th in rows[0].find_all('th')]
            
            # Extract data rows
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    service_name = cells[0].get_text().strip()
                    
                    # Parse benefits for each HMO
                    maccabi_benefits = self.parse_benefits_cell(cells[1].get_text())
                    meuhedet_benefits = self.parse_benefits_cell(cells[2].get_text())
                    clalit_benefits = self.parse_benefits_cell(cells[3].get_text())
                    
                    table_data[service_name] = {
                        'מכבי': maccabi_benefits,
                        'מאוחדת': meuhedet_benefits, 
                        'כללית': clalit_benefits
                    }
        
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
        
        return table_data
    
    def parse_benefits_cell(self, cell_text: str) -> Dict:
        """Parse benefits for each insurance tier from table cell"""
        benefits = {'זהב': '', 'כסף': '', 'ארד': ''}
        
        try:
            # Split by line breaks and clean
            lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
            
            current_tier = None
            for line in lines:
                # Check if line starts with tier name
                if line.startswith('זהב:'):
                    current_tier = 'זהב'
                    benefits[current_tier] = line.replace('זהב:', '').strip()
                elif line.startswith('כסף:'):
                    current_tier = 'כסף' 
                    benefits[current_tier] = line.replace('כסף:', '').strip()
                elif line.startswith('ארד:'):
                    current_tier = 'ארד'
                    benefits[current_tier] = line.replace('ארד:', '').strip()
                elif current_tier and not any(line.startswith(tier + ':') for tier in ['זהב', 'כסף', 'ארד']):
                    # Continuation of current tier
                    benefits[current_tier] += ' ' + line
        
        except Exception as e:
            logger.error(f"Error parsing benefits cell: {e}")
        
        return benefits
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extract contact information"""
        contact_info = {}
        
        try:
            # Look for contact sections
            h3_elements = soup.find_all('h3')
            
            for h3 in h3_elements:
                if 'טלפון' in h3.get_text() or 'לפרטים' in h3.get_text():
                    # Get the following ul element
                    next_ul = h3.find_next_sibling('ul')
                    if next_ul:
                        li_elements = next_ul.find_all('li')
                        for li in li_elements:
                            text = li.get_text()
                            if 'מכבי:' in text:
                                contact_info['מכבי'] = text.replace('מכבי:', '').strip()
                            elif 'מאוחדת:' in text:
                                contact_info['מאוחדת'] = text.replace('מאוחדת:', '').strip()
                            elif 'כללית:' in text:
                                contact_info['כללית'] = text.replace('כללית:', '').strip()
        
        except Exception as e:
            logger.error(f"Error extracting contact info: {e}")
        
        return contact_info
    
    def get_service_benefits(self, service_type: str, hmo_name: str, tier: str, 
                           specific_service: Optional[str] = None) -> str:
        """Get benefits for specific service, HMO and tier"""
        
        logger.info(f"Getting service benefits: service_type={service_type}, hmo_name={hmo_name}, tier={tier}")
        
        try:
            if service_type not in self.services_data:
                logger.warning(f"Service type {service_type} not found in services_data")
                return f"מצטער, לא נמצא מידע על שירותי {service_type}"
            
            service_data = self.services_data[service_type]
            logger.info(f"Found service data for {service_type}")
            
            if not service_data.get('benefits_table'):
                logger.warning(f"No benefits_table found for {service_type}")
                return f"מצטער, לא נמצא מידע על הטבות עבור {service_type}"
            
            benefits_table = service_data['benefits_table']
            logger.info(f"Benefits table keys: {list(benefits_table.keys())}")
            
            # If specific service requested, look for it
            if specific_service:
                logger.info(f"Looking for specific service: {specific_service}")
                for service_name, benefits in benefits_table.items():
                    if specific_service.lower() in service_name.lower():
                        logger.info(f"Found matching service: {service_name}")
                        if hmo_name in benefits and tier in benefits[hmo_name]:
                            benefit_text = benefits[hmo_name][tier]
                            logger.info(f"Found benefit text: {benefit_text}")
                            return f"עבור {service_name} ב{hmo_name} במסלול {tier}:\n{benefit_text}"
                
                logger.warning(f"No specific service found for: {specific_service}")
                return f"לא נמצא מידע ספציפי על {specific_service}"
            
            # Return all benefits for the HMO and tier
            response = f"ההטבות שלך עבור {service_data['title']} ב{hmo_name} במסלול {tier}:\n\n"
            
            found_benefits = False
            for service_name, benefits in benefits_table.items():
                logger.info(f"Processing service: {service_name}")
                logger.info(f"  Available HMOs: {list(benefits.keys())}")
                
                if hmo_name in benefits:
                    logger.info(f"  Found HMO {hmo_name}, available tiers: {list(benefits[hmo_name].keys())}")
                    
                    if tier in benefits[hmo_name]:
                        benefit_text = benefits[hmo_name][tier]
                        logger.info(f"  Found benefit for {tier}: {benefit_text}")
                        
                        if benefit_text.strip():
                            response += f"• {service_name}: {benefit_text}\n\n"
                            found_benefits = True
                        else:
                            logger.warning(f"  Empty benefit text for {service_name}")
                    else:
                        logger.warning(f"  Tier {tier} not found for {service_name} in {hmo_name}")
                else:
                    logger.warning(f"  HMO {hmo_name} not found for {service_name}")
            
            if not found_benefits:
                logger.warning("No benefits found for the specified criteria")
                return f"לא נמצאו הטבות עבור {hmo_name} במסלול {tier}"
            
            # Add contact info
            if service_data.get('contact_info') and hmo_name in service_data['contact_info']:
                response += f"\nליצירת קשר: {service_data['contact_info'][hmo_name]}"
            
            logger.info(f"Final response length: {len(response)}")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error getting service benefits: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "מצטער, אירעה שגיאה בחיפוש המידע"
    
    def search_services(self, query: str) -> List[str]:
        """Search for services matching the query"""
        matches = []
        
        query_lower = query.lower()
        logger.info(f"Searching for services in query: '{query}' (lower: '{query_lower}')")
        logger.info(f"Available service types: {list(self.services_data.keys())}")
        
        # Search in service types
        for service_type in self.services_data.keys():
            logger.info(f"Checking service type: {service_type}")
            
            if any(keyword in service_type for keyword in ['dental', 'dentel', 'שיניים']):
                if any(keyword in query_lower for keyword in ['שיניים', 'dental', 'דנטל', 'שן', 'טיפולי שיניים']):
                    logger.info(f"Matched dental service: {service_type}")
                    matches.append('dentel')
            elif any(keyword in service_type for keyword in ['optometry', 'אופטומטריה']):
                if any(keyword in query_lower for keyword in ['עיניים', 'ראייה', 'משקפיים', 'עדשות', 'optometry', 'בדיקות ראייה']):
                    logger.info(f"Matched optometry service: {service_type}")
                    matches.append('optometry')
            elif any(keyword in service_type for keyword in ['pregnancy', 'pragrency', 'הריון']):
                pregnancy_keywords = ['הריון', 'לידה', 'pregnancy', 'בריאות האישה', 'נשים הרות', 'הרות', 'מעקב הריון']
                logger.info(f"Checking pregnancy keywords: {pregnancy_keywords}")
                for keyword in pregnancy_keywords:
                    if keyword in query_lower:
                        logger.info(f"Found pregnancy keyword '{keyword}' in query")
                        matches.append('pragrency')
                        break
            elif any(keyword in service_type for keyword in ['alternative', 'אלטרנטיב']):
                if any(keyword in query_lower for keyword in ['אלטרנטיב', 'רפואה משלימה', 'alternative']):
                    logger.info(f"Matched alternative service: {service_type}")
                    matches.append('alternative')
            elif any(keyword in service_type for keyword in ['communication', 'תקשורת']):
                if any(keyword in query_lower for keyword in ['תקשורת', 'דיבור', 'שמיעה', 'communication']):
                    logger.info(f"Matched communication service: {service_type}")
                    matches.append('communication_clinic')
            elif any(keyword in service_type for keyword in ['workshops', 'סדנאות']):
                if any(keyword in query_lower for keyword in ['סדנאות', 'הרצאות', 'workshops', 'קורסים']):
                    logger.info(f"Matched workshops service: {service_type}")
                    matches.append('workshops')
        
        logger.info(f"Final matches: {matches}")
        return matches
    
    def extract_hypothetical_params(self, query: str) -> Dict[str, Optional[str]]:
        """Extract hypothetical HMO and tier from user query"""
        import re
        
        query_lower = query.lower()
        result = {'hmo': None, 'tier': None}
        
        # Detect hypothetical scenarios
        hypothetical_phrases = [
            'אם הייתי', 'לו הייתי', 'אילו הייתי', 'מה אם', 'מה לו',
            'if i was', 'if i were', 'what if', 'suppose i was'
        ]
        
        is_hypothetical = any(phrase in query_lower for phrase in hypothetical_phrases)
        
        if not is_hypothetical:
            # Check for direct tier/HMO mentions that might be hypothetical
            tier_mentions = ['זהב', 'כסף', 'ארד', 'gold', 'silver', 'bronze']
            hmo_mentions = ['מכבי', 'מאוחדת', 'כללית', 'maccabi', 'meuhedet', 'clalit']
            
            # If tier or HMO is mentioned, consider it potentially hypothetical
            if any(tier in query_lower for tier in tier_mentions) or any(hmo in query_lower for hmo in hmo_mentions):
                is_hypothetical = True
        
        if is_hypothetical:
            # Extract HMO
            if any(word in query_lower for word in ['מכבי', 'maccabi']):
                result['hmo'] = 'מכבי'
            elif any(word in query_lower for word in ['מאוחדת', 'meuhedet']):
                result['hmo'] = 'מאוחדת'
            elif any(word in query_lower for word in ['כללית', 'clalit']):
                result['hmo'] = 'כללית'
            
            # Extract tier
            if any(word in query_lower for word in ['זהב', 'gold']):
                result['tier'] = 'זהב'
            elif any(word in query_lower for word in ['כסף', 'silver']):
                result['tier'] = 'כסף'
            elif any(word in query_lower for word in ['ארד', 'bronze']):
                result['tier'] = 'ארד'
        
        return result
    
    def get_available_services(self) -> List[str]:
        """Get list of available service types"""
        return list(self.services_data.keys())

