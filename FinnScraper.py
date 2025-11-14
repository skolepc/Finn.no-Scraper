# FinnScraper.py
import customtkinter as ctk
import re
from urllib.parse import quote
import webbrowser
from threading import Thread
from PIL import Image, ImageTk
import io
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk
import json
import os
import logging
import sys
import subprocess

# Import from APICrypted.py
from APICrypted import get_page_html, get_image_content

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MARKET_LIST = {
    'eiendom': 'realestate/forsale/search',
    'bil': 'mobility/search/car',
    'torget': 'recommerce/forsale/search',
    'mc': 'mobility/search/mc',
    'båt': 'mobility/search/boat'
}

LOCATIONS = {
    'Agder': '0.22042',
    'Akershus': '0.20003',
    'Buskerud': '0.20007',
    'Finnmark': '0.20020',
    'Innlandet': '0.22034',
    'Møre og Romsdal': '0.20015',
    'Nordland': '0.20018',
    'Oslo': '0.20061',
    'Rogaland': '0.20012',
    'Svalbard': '0.20506',
    'Telemark': '0.20009',
    'Troms': '0.20019',
    'Trøndelag': '0.20016',
    'Vestfold': '0.20008',
    'Vestland': '0.22046',
    'Østfold': '0.20002'
}

SORT_OPTIONS = {
    'relevant': 0,
    'nyeste': 1,
    'eldste': 2,
    'lav': 3,
    'høy': 4,
    'nærmest': 5
}

CONDITION_OPTIONS = {
    'All': None,
    'Helt ny - Uåpnet/med kvittering': 1,
    'Som ny - ikke synlig brukt': 2,
    'Pent brukt - i god stand': 3,
    'Godt brukt - merker på gjenstanden': 4,
    'Må fikses - Noen mangler / ødelagte deler': 5
}



class FinnScraperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("FINN.no Advanced Scraper")
        self.geometry(f"{1200}x{650}")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Fade-in on launch
        self.attributes('-alpha', 0.0)
        self.after(100, self._fade_in_window)

        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((0, 2), weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=150, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="FINN Scraper", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.toggle_button = ctk.CTkButton(self.sidebar_frame, text="Toggle Layout", command=self.toggle_layout,
                                          fg_color="#1f538d", hover_color="#2a6db0")
        self.toggle_button.grid(row=1, column=0, padx=20, pady=10)

        self.save_button = ctk.CTkButton(self.sidebar_frame, text="Save Settings", command=self.save_settings,
                                        fg_color="#1f538d", hover_color="#2a6db0")
        self.save_button.grid(row=2, column=0, padx=20, pady=10)

        self.load_button = ctk.CTkButton(self.sidebar_frame, text="Load Settings", command=self.load_settings,
                                        fg_color="#1f538d", hover_color="#2a6db0")
        self.load_button.grid(row=3, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance:", anchor="w")
        self.appearance_mode_label.grid(row=4, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                            command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=5, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

        # Settings frame
        self.settings_frame = ctk.CTkFrame(self, width=300, corner_radius=10)
        self.settings_frame.grid(row=0, column=2, padx=(10, 20), pady=(20, 10), sticky="nsew")
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_rowconfigure(1, weight=1)

        # Search options frame
        self.search_options_frame = ctk.CTkFrame(self.settings_frame, corner_radius=10)
        self.search_options_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.search_options_frame.grid_columnconfigure(0, weight=1)

        self.market_label = ctk.CTkLabel(self.search_options_frame, text="Market:", font=ctk.CTkFont(size=14))
        self.market_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.market_var = ctk.StringVar(value='torget')
        self.market_combobox = ctk.CTkComboBox(self.search_options_frame, values=list(MARKET_LIST.keys()),
                                              variable=self.market_var, command=self.on_market_change, width=200)
        self.market_combobox.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        self.sort_label = ctk.CTkLabel(self.search_options_frame, text="Sort:", font=ctk.CTkFont(size=14))
        self.sort_label.grid(row=2, column=0, padx=10, pady=(5, 5), sticky="w")
        self.sort_var = ctk.StringVar(value='relevant')
        self.sort_combobox = ctk.CTkComboBox(self.search_options_frame, values=list(SORT_OPTIONS.keys()),
                                            variable=self.sort_var, width=200)
        self.sort_combobox.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="w")

        self.pages_label = ctk.CTkLabel(self.search_options_frame, text="Pages:", font=ctk.CTkFont(size=14))
        self.pages_label.grid(row=4, column=0, padx=10, pady=(5, 5), sticky="w")
        self.pages_var = ctk.IntVar(value=1)
        self.pages_entry = ctk.CTkEntry(self.search_options_frame, textvariable=self.pages_var, width=100)
        self.pages_entry.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="w")

        self.condition_frame = ctk.CTkFrame(self.search_options_frame, fg_color="transparent")
        self.condition_frame.grid(row=6, column=0, padx=10, pady=(5, 10), sticky="w")
        self.condition_label = ctk.CTkLabel(self.condition_frame, text="Condition:", font=ctk.CTkFont(size=14))
        self.condition_label.pack(side=ctk.LEFT, padx=(0, 5))
        self.condition_var = ctk.StringVar(value='All')
        self.condition_combobox = ctk.CTkComboBox(self.condition_frame, values=list(CONDITION_OPTIONS.keys()),
                                                 variable=self.condition_var, width=150)
        self.condition_combobox.pack(side=ctk.LEFT)

        # Locations frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.settings_frame, label_text="Locations (Multi-select)", height=300,
                                                     fg_color="#2a2a2a", corner_radius=10)
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)
        self.location_vars = {}
        for i, area in enumerate(LOCATIONS.keys()):
            var = ctk.BooleanVar()
            checkbox = ctk.CTkCheckBox(self.scrollable_frame, text=area, variable=var, font=ctk.CTkFont(size=12))
            checkbox.grid(row=i // 2, column=i % 2, padx=5, pady=3, sticky="w")
            self.location_vars[area] = var

        # Results frame
        self.results_frame = ctk.CTkFrame(self, corner_radius=10)
        self.results_frame.grid(row=0, column=1, padx=(20, 10), pady=(20, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        columns = ('Title', 'Price', 'Place', 'Time', 'Seller', 'URL')
        self.tree = ttk.Treeview(self.results_frame, columns=columns, show='headings', height=20)
        self.tree.heading('Title', text='Title')
        self.tree.heading('Price', text='Price')
        self.tree.heading('Place', text='Place')
        self.tree.heading('Time', text='Time')
        self.tree.heading('Seller', text='Seller')
        self.tree.heading('URL', text='URL')
        self.tree.column('Title', width=350, anchor=tk.W)
        self.tree.column('Price', width=120, anchor=tk.W)
        self.tree.column('Place', width=120, anchor=tk.W)
        self.tree.column('Time', width=100, anchor=tk.W)
        self.tree.column('Seller', width=120, anchor=tk.W)
        self.tree.column('URL', width=200, anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Bottom frame
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=1, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(self.bottom_frame, placeholder_text="Search term (e.g., iphone 17)", height=35)
        self.search_entry.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.search_var = ctk.StringVar(value='iphone 17')
        self.search_entry.configure(textvariable=self.search_var)

        self.button_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.button_frame.grid(row=0, column=1, padx=0, pady=5, sticky="e")
        self.scrape_button = ctk.CTkButton(self.button_frame, text="🔍 Scrape", command=self.on_scrape,
                                          fg_color="#1f538d", hover_color="#2a6db0", width=100)
        self.scrape_button.pack(side=tk.LEFT, padx=5)
        self.clear_button = ctk.CTkButton(self.button_frame, text="Clear", command=self.clear_inputs,
                                         fg_color="#8b0000", hover_color="#b22222", width=100)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.status_var = ctk.StringVar(value="Ready to scrape...")
        self.status_label = ctk.CTkLabel(self.bottom_frame, textvariable=self.status_var, font=ctk.CTkFont(size=12))
        self.status_label.grid(row=1, column=0, columnspan=2, padx=0, pady=(5, 5), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, width=300)
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=0, pady=(5, 0), sticky="w")
        self.progress_bar.set(0)

        # Internal vars
        self.items = []
        self.image_cache = {}  # Thumbnails (100x100)
        self.large_image_cache = {}  # Large images (300x300)
        self.current_image_idx = None
        self.show_delay_id = None
        self.hovered_row = None
        self.popup = None
        self.image_alpha = 0.0
        self.thumbnail_size = (100, 100)
        self.large_size = (300, 300)
        self.layout_swapped = False
        self.popup_offset_x = 10
        self.popup_offset_y = 10
        self.on_market_change()

        # Bind events
        self.tree.bind('<Double-1>', self.on_item_double_click)
        self.tree.bind('<Motion>', self.on_hover)
        self.tree.bind('<Leave>', self.on_leave)
        self.tree.bind('<Button-1>', self.open_browser_url)

    def _fade_in_window(self):
        alpha = self.attributes('-alpha')
        alpha += 0.05
        if alpha < 1:
            self.attributes('-alpha', alpha)
            self.after(30, self._fade_in_window)
        else:
            self.attributes('-alpha', 1.0)

    def _fade_popup(self, popup, idx):
        if popup and idx == self.current_image_idx and idx in self.image_cache:
            self.image_alpha += 0.1
            if self.image_alpha <= 1.0:
                popup.attributes('-alpha', self.image_alpha)
                self.after(50, lambda: self._fade_popup(popup, idx))
            else:
                self.image_alpha = 1.0
                popup.attributes('-alpha', 1.0)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def on_market_change(self, event=None):
        if self.market_var.get() == 'torget':
            self.condition_frame.grid(row=6, column=0, padx=10, pady=(5, 10), sticky="w")
        else:
            self.condition_frame.grid_remove()

    def toggle_layout(self):
        self.layout_swapped = not self.layout_swapped
        self.results_frame.grid_forget()
        self.settings_frame.grid_forget()
        if self.layout_swapped:
            self.results_frame.grid(row=0, column=2, padx=(10, 20), pady=(20, 10), sticky="nsew")
            self.settings_frame.grid(row=0, column=1, padx=(20, 10), pady=(20, 10), sticky="nsew")
        else:
            self.results_frame.grid(row=0, column=1, padx=(20, 10), pady=(20, 10), sticky="nsew")
            self.settings_frame.grid(row=0, column=2, padx=(10, 20), pady=(20, 10), sticky="nsew")
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def save_settings(self):
        settings = {
            'market': self.market_var.get(),
            'sort': self.sort_var.get(),
            'pages': self.pages_var.get(),
            'condition': self.condition_var.get(),
            'search': self.search_var.get(),
            'locations': {area: var.get() for area, var in self.location_vars.items()}
        }
        try:
            with open('finn_settings.json', 'w') as f:
                json.dump(settings, f)
            self.status_var.set("Settings saved successfully!")
        except Exception as e:
            self.status_var.set(f"Error saving settings: {str(e)}")

    def load_settings(self):
        try:
            with open('finn_settings.json', 'r') as f:
                settings = json.load(f)
            self.market_var.set(settings.get('market', 'torget'))
            self.sort_var.set(settings.get('sort', 'relevant'))
            self.pages_var.set(settings.get('pages', 1))
            self.condition_var.set(settings.get('condition', 'All'))
            self.search_var.set(settings.get('search', 'iphone 17'))
            for area, var in self.location_vars.items():
                var.set(settings.get('locations', {}).get(area, False))
            self.on_market_change()
            self.status_var.set("Settings loaded successfully!")
        except FileNotFoundError:
            self.status_var.set("No saved settings found.")
        except Exception as e:
            self.status_var.set(f"Error loading settings: {str(e)}")

    def clear_inputs(self):
        self.search_var.set("")
        self.market_var.set('torget')
        self.sort_var.set('relevant')
        self.pages_var.set(1)
        self.condition_var.set('All')
        for var in self.location_vars.values():
            var.set(False)
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.current_image_idx = None
        self.on_market_change()
        self.status_var.set("Inputs cleared.")

    def scrape_torget(self, search, sort, location_codes, condition, pages, base_url):
        param_list = [f"q={quote(search)}", f"sort={SORT_OPTIONS[sort]}"]
        for loc_code in location_codes:
            param_list.append(f"location={loc_code}")
        if condition and condition != 'All':
            param_list.append(f"condition={CONDITION_OPTIONS[condition]}")
        base_query_string = "&".join(param_list)
        html_url = f"{base_url}?{base_query_string}"

        self.status_var.set("Fetching data...")
        self.progress_bar.set(0)
        self.update()

        try:
            all_items = []
            total_hits = 'Unknown'
            for page in range(1, pages + 1):
                page_url = html_url if page == 1 else f"{html_url}&page={page}"
                logging.debug(f"Scraping URL: {page_url}")
                html = get_page_html(page_url)
                if html is None:
                    raise Exception("Failed to fetch page HTML")

                if page == 1:
                    hits_match = re.search(r'(\d+(?:\s*\d+)?)\s*(?:result|annonse)', html)
                    total_hits = hits_match.group(1).replace(' ', '') if hits_match else 'Unknown'

                soup = BeautifulSoup(html, 'html.parser')
                ads = soup.find_all('article', {'class': lambda x: x and 'sf-search-ad' in str(x) if x else False})
                logging.debug(f"Found {len(ads)} ads on page {page}")
                for ad_idx, ad in enumerate(ads):
                    # Try different selectors for images
                    img = ad.find('img')
                    if not img:
                        img = ad.find('div', class_=lambda x: x and 'image' in str(x).lower()) if ad.find('div') else None
                        if img:
                            style = img.get('style', '')
                            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                            if match:
                                image = match.group(1)
                            else:
                                image = ''
                        else:
                            image = ''
                    else:
                        image = img.get('src', '') or img.get('data-src', '') or ''
                    
                    logging.debug(f"Ad {ad_idx}: image = {image}")

                    # Title and URL
                    h2 = ad.find('h2', class_='h4')
                    if not h2:
                        h2 = ad.find('h2') or ad.find('h3') or ad.find('a', class_=lambda x: x and 'title' in str(x).lower())
                    title = ''
                    url_ = ''
                    if h2:
                        a = h2.find('a') if h2.name == 'h2' else h2 if h2.name == 'a' else h2.find('a')
                        if a:
                            title = a.get_text(strip=True)
                            href = a.get('href', '')
                            url_ = 'https://www.finn.no' + href if href.startswith('/') else href

                    if not title:
                        continue

                    logging.debug(f"Ad {ad_idx}: title = {title[:50]}...")

                    # Price
                    price_str = 'Ingen pris'
                    price_selectors = [
                        ad.find('span', string=re.compile(r'[\d\s]+kr')),
                        ad.find('span', class_=lambda x: x and 'price' in str(x).lower()),
                        ad.find('div', string=re.compile(r'[\d\s]+kr')),
                        ad.find('span', class_='text-xl font-bold'),
                        ad.find('span', class_='price'),
                        ad.find('div', class_='price')
                    ]
                    for selector in price_selectors:
                        if selector:
                            price_str = selector.get_text(strip=True)
                            if price_str and re.search(r'\d', price_str):
                                break

                    logging.debug(f"Ad {ad_idx}: price = {price_str}")

                    # Place and Time
                    place = ''
                    time_str = ''
                    info_div = ad.find('div', class_=lambda x: x and 'text-xs' in str(x) and 'flex' in str(x) and 'justify-between' in str(x))
                    if not info_div:
                        info_div = ad.find('div', class_='text-xs')
                        if not info_div:
                            info_div = ad.find('div', class_='location')
                    if info_div:
                        spans = info_div.find_all('span')
                        if len(spans) >= 2:
                            place = spans[0].get_text(strip=True)
                            time_str = spans[1].get_text(strip=True).lstrip('· ').strip()
                        elif len(spans) >= 1:
                            place = spans[0].get_text(strip=True)

                    logging.debug(f"Ad {ad_idx}: place = {place}, time = {time_str}")

                    all_items.append({
                        'title': title,
                        'price': price_str,
                        'place': place,
                        'time': time_str,
                        'seller': '',  # No seller for torget
                        'url': url_,
                        'image': image
                    })

                self.progress_bar.set(page / pages)
                self.update()

            self.status_var.set(f"Total hits: {total_hits}")
            return all_items, html_url
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            logging.error(f"Scraping error: {str(e)}")
            return [], html_url

    def scrape_bil(self, search, sort, location_codes, pages, base_url):
        param_list = [f"q={quote(search)}", f"sort={SORT_OPTIONS[sort]}"]
        for loc_code in location_codes:
            param_list.append(f"location={loc_code}")
        param_list.append('registration_class=1')
        base_query_string = "&".join(param_list)
        html_url = f"{base_url}?{base_query_string}"

        self.status_var.set("Fetching data...")
        self.progress_bar.set(0)
        self.update()

        try:
            all_items = []
            total_hits = 'Unknown'
            for page in range(1, pages + 1):
                page_url = html_url if page == 1 else f"{html_url}&page={page}"
                logging.debug(f"Scraping URL: {page_url}")
                html = get_page_html(page_url)
                if html is None:
                    raise Exception("Failed to fetch page HTML")

                if page == 1:
                    # Extract total hits from meta description or title
                    hits_match = re.search(r'(\d+(?:\s*\d+)?)\s*annonser', html)
                    total_hits = hits_match.group(1).replace(' ', '') if hits_match else 'Unknown'

                soup = BeautifulSoup(html, 'html.parser')

                # Try to parse from SEO structured data
                script = soup.find('script', {'id': 'seoStructuredData'})
                if script:
                    try:
                        data = json.loads(script.string)
                        items = data.get('mainEntity', {}).get('itemListElement', [])
                        logging.debug(f"Found {len(items)} items from structured data on page {page}")
                        for item_data in items:
                            product = item_data.get('item', {})
                            title = product.get('name', '')
                            offers = product.get('offers', {})
                            price_str = f"{offers.get('price', '')} kr" if offers.get('price') else 'Ingen pris'
                            url_ = product.get('url', '')
                            image = product.get('image', '')
                            place = ''  # Not available in structured data
                            time_str = ''  # Not available
                            seller = ''  # Not available

                            if title:
                                all_items.append({
                                    'title': title,
                                    'price': price_str,
                                    'place': place,
                                    'time': time_str,
                                    'seller': seller,
                                    'url': url_,
                                    'image': image
                                })
                    except json.JSONDecodeError as je:
                        logging.error(f"JSON decode error: {je}")

                # Fallback to HTML parsing if structured data not sufficient
                if not all_items:
                    ads = soup.find_all('article', {'data-testid': lambda x: x and 'search-result' in str(x) if x else False})
                    if not ads:
                        ads = soup.find_all('div', class_=lambda x: x and 'ad' in str(x).lower() if x else False)
                    logging.debug(f"Found {len(ads)} ads from HTML on page {page}")
                    for ad_idx, ad in enumerate(ads):
                        # Title and URL - try general selectors
                        a_tag = ad.find('a')
                        title = ''
                        url_ = ''
                        if a_tag:
                            title = a_tag.get_text(strip=True)
                            href = a_tag.get('href', '')
                            url_ = 'https://www.finn.no' + href if href.startswith('/') else href

                        if not title:
                            continue

                        # Price
                        price_str = 'Ingen pris'
                        price_elem = ad.find('span', {'data-testid': 'price'}) or ad.find('h2', {'data-testid': 'price'}) or ad.find(string=re.compile(r'\d+\s*kr'))
                        if price_elem:
                            price_str = price_elem.get_text(strip=True)

                        # Place
                        place_elem = ad.find('span', {'data-testid': 'location'}) or ad.find(class_=re.compile(r'location'))
                        place = place_elem.get_text(strip=True) if place_elem else ''

                        # Time
                        time_elem = ad.find('time') or ad.find(class_=re.compile(r'time'))
                        time_str = time_elem.get_text(strip=True) if time_elem else ''

                        # Seller
                        seller_elem = ad.find('span', {'data-testid': 'seller-type'}) or ad.find(class_=re.compile(r'seller'))
                        seller = seller_elem.get_text(strip=True) if seller_elem else ''

                        # Image
                        img_elem = ad.find('img')
                        image = img_elem.get('src') if img_elem else ''

                        all_items.append({
                            'title': title,
                            'price': price_str,
                            'place': place,
                            'time': time_str,
                            'seller': seller,
                            'url': url_,
                            'image': image
                        })

                self.progress_bar.set(page / pages)
                self.update()

            self.status_var.set(f"Total hits: {total_hits}")
            return all_items, html_url
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            logging.error(f"Scraping error: {str(e)}")
            return [], html_url

    def scrape(self, market, search, sort, location_codes, condition, pages):
        market_key = MARKET_LIST[market]
        base_url = f"https://www.finn.no/{market_key}"
        if market == 'bil':
            return self.scrape_bil(search, sort, location_codes, pages, base_url)
        elif market == 'torget':
            return self.scrape_torget(search, sort, location_codes, condition, pages, base_url)
        else:
            # Fallback for other markets (use torget logic for now)
            return self.scrape_torget(search, sort, location_codes, condition, pages, base_url)

    def on_scrape(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.items = []
        self.image_cache.clear()
        self.large_image_cache.clear()
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.current_image_idx = None
        Thread(target=self._run_scrape, daemon=True).start()

    def _run_scrape(self):
        market = self.market_var.get()
        search = self.search_var.get()
        sort = self.sort_var.get()
        location_codes = [LOCATIONS[area] for area, var in self.location_vars.items() if var.get()]
        condition = self.condition_var.get() if self.market_var.get() == 'torget' else None
        pages = self.pages_var.get()

        items, html_url = self.scrape(market, search, sort, location_codes, condition, pages)
        self.after(0, lambda: self._update_results(items, html_url))

    def _update_results(self, items, html_url):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.items = items
        for idx, item in enumerate(items):
            self.tree.insert('', 'end', iid=str(idx), values=(
                item['title'],
                item['price'],
                item['place'],
                item['time'],
                item['seller'],
                item['url']
            ))
        self.status_var.set(f"Found {len(items)} items. Browser URL: {html_url}")
        self.progress_bar.set(0)

    def on_hover(self, event):
        row = self.tree.identify_row(event.y)
        if row != self.hovered_row:
            if self.show_delay_id:
                self.after_cancel(self.show_delay_id)
                self.show_delay_id = None
            if self.popup:
                self.popup.destroy()
                self.popup = None
            self.current_image_idx = None
            self.image_alpha = 0.0
            self.hovered_row = row
            if row:
                try:
                    idx = int(row)
                    if idx not in self.image_cache:
                        Thread(target=self._load_thumbnail, args=(idx,), daemon=True).start()
                    self.show_delay_id = self.after(1850, lambda: self._check_and_show(idx, event.x_root, event.y_root))
                except (ValueError, IndexError):
                    pass
        else:
            if self.popup:
                self._update_popup_position(event.x_root, event.y_root)

    def _load_thumbnail(self, idx):
        image_url = self.items[idx]['image']
        if not image_url:
            logging.warning(f"No image URL for item {idx}")
            return
        try:
            logging.debug(f"Loading thumbnail for item {idx}: {image_url}")
            content = get_image_content(image_url)
            if content:
                img = Image.open(io.BytesIO(content))
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_cache[idx] = photo
                self.after(0, lambda: self._post_load_show(idx))
        except Exception as e:
            logging.error(f"Error loading thumbnail for item {idx}: {str(e)}")

    def _load_large_image(self, idx):
        image_url = self.items[idx]['image']
        if not image_url:
            logging.warning(f"No image URL for large image {idx}")
            return None
        try:
            logging.debug(f"Loading large image for item {idx}: {image_url}")
            content = get_image_content(image_url)
            if content:
                img = Image.open(io.BytesIO(content))
                img.thumbnail(self.large_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.large_image_cache[idx] = photo
                return photo
        except Exception as e:
            logging.error(f"Error loading large image for item {idx}: {str(e)}")
            return None

    def _post_load_show(self, idx):
        if self.hovered_row == idx and self.show_delay_id is None and idx in self.image_cache:
            x = self.winfo_pointerx() + self.popup_offset_x
            y = self.winfo_pointery() + self.popup_offset_y
            self._show_popup(idx, x, y)

    def _check_and_show(self, idx, x, y):
        self.show_delay_id = None
        if self.hovered_row == idx and idx in self.image_cache:
            self._show_popup(idx, x + self.popup_offset_x, y + self.popup_offset_y)

    def _show_popup(self, idx, x, y):
        if self.popup:
            self.popup.destroy()
        self.popup = ctk.CTkToplevel(self)
        self.popup.overrideredirect(True)
        self.popup.wm_attributes('-topmost', True)
        self.popup.attributes('-alpha', 0.0)
        label = ctk.CTkLabel(self.popup, image=self.image_cache[idx], text="")
        label.pack()
        w, h = self.thumbnail_size
        self.popup.geometry(f"{w}x{h}+{x}+{y}")
        self.current_image_idx = idx
        self.image_alpha = 0.0
        label.bind("<Button-1>", lambda event: self.on_popup_click(idx))
        self._fade_popup(self.popup, idx)

    def _update_popup_position(self, x, y):
        if self.popup:
            w = self.thumbnail_size[0]
            h = self.thumbnail_size[1]
            self.popup.geometry(f"{w}x{h}+{x + self.popup_offset_x}+{y + self.popup_offset_y}")

    def on_popup_click(self, idx):
        if idx not in self.large_image_cache:
            photo = self._load_large_image(idx)
            if photo:
                self.large_image_cache[idx] = photo
        if idx in self.large_image_cache:
            large_popup = ctk.CTkToplevel(self)
            large_popup.title("Image Preview")
            large_popup.geometry(f"{self.large_size[0]}x{self.large_size[1]}")
            label = ctk.CTkLabel(large_popup, image=self.large_image_cache[idx], text="")
            label.pack()
            large_popup.transient(self)
            large_popup.grab_set()

    def on_leave(self, event):
        if self.show_delay_id:
            self.after_cancel(self.show_delay_id)
            self.show_delay_id = None
        self.hovered_row = None
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.current_image_idx = None
        self.image_alpha = 0.0

    def open_browser_url(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#6":  # URL is the 6th column
                selection = self.tree.selection()
                if selection:
                    item = self.tree.item(selection[0])
                    url = item['values'][5]
                    webbrowser.open(url)
        return "break"

    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            url = item['values'][5]  # URL is the 6th value
            webbrowser.open(url)



if __name__ == "__main__":

    def launch_updater():
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            api_path = os.path.join(script_dir, "FinnAPI-ENC.py")
            
            if os.path.exists(api_path):
                if sys.platform == "win32":
                    subprocess.Popen(
                        [sys.executable, api_path],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    subprocess.Popen(
                        [sys.executable, api_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                logging.info("Starting...")
            else:
                logging.warning(f"FinnAPI-ENC.py not found!!!")
                FinnScraperGUI.close()
        except Exception as e:
            logging.error(f"Failed to launch APICrypted..")

    launch_updater()

    app = FinnScraperGUI()
    app.mainloop()