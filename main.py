import os
import sys
import json
import time
import requests
import traceback
import threading
import importlib.util
import types
import inspect
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES_PATH = os.path.join(PROJECT_ROOT, 'sources')
USERDATA_PATH = os.path.join(PROJECT_ROOT, 'userdata')
CONFIG_FILE = os.path.join(USERDATA_PATH, 'config.json')
if not os.path.exists(USERDATA_PATH): os.makedirs(USERDATA_PATH)
if not os.path.exists(SOURCES_PATH): os.makedirs(SOURCES_PATH)
if PROJECT_ROOT not in sys.path: sys.path.append(PROJECT_ROOT)
alt_resolve = os.path.join(PROJECT_ROOT, 'resolveurl')
if alt_resolve not in sys.path: sys.path.append(alt_resolve)
sys.modules['resources'] = types.ModuleType('resources')
sys.modules['resources.lib'] = types.ModuleType('resources.lib')
try:
    import modules
    sys.modules['resources.lib.modules'] = modules
except ImportError:
    print("[WARNING] The 'modules' folder is missing from the root directory!")

sys.argv[:] = ['plugin://plugin.video.universal/', '1', '']

try:
    import resolveurl
except ImportError:
    print("[WARNING] ResolveURL not found in sys.path!")
    resolveurl = None

DEFAULT_WHITELIST = [
    'vidsrc.me', '2embed.me', 'vidsrc.to', 'vidlink.org', 'vidsrc.mov', 
    '2embed.ru', '2embed.cc', 'goload.io', 'goload.pro', 'vidembed.cc',
    'vidcloud9.com', 'voxzer.org', 'ronemo.com', 'streamembed.net',
    'databasegdriveplayer.co', 'bnwmovies.com', 'levidia.ch', 'mp4hydra.top',
    'vidsrc.fyi', 'vidrock.net', 'vidnest.fun', 'vidking.net',
    'vidfast.pro', 'vidup.to', 'videasy.net', '111movies.com',
    'multiembed.mov', 'superflixapi.co', 'peachify.top', 'gdriveplayer.us',
    'gomo.to', 'vsembed.ru', 'cloudnestra.com', 'putgate.org', 'goodstream.cc',
    'stigstream.ru', 'linkbin.me', 'hlspanel.xyz', 'furher.in', 'playerhost.net',
    'gomostream.com', 'gomoplayer.com', 'database.gdriveplayer.co', 'database.gdriveplayer.io',
    'database.gdriveplayer.me', 'database.gdriveplayer.us', 'database.gdriveplayer.xyz',
    'downloads-anymovies.co', 'downloads-anymovies.com', 'mp4hydra.org', 'mp4hydra.info',
    'naijavault.com', 'seriezloaded.com.ng', 'stagatv.com', 'tvseries.in', 'mobiletvshows.site',
    'fzmovies.live'
]

def gather_resolveurl_hosts():
    hosts = set()

    if resolveurl and hasattr(resolveurl, 'relevant_resolvers'):
        try:
            resolvers = resolveurl.relevant_resolvers(order_matters=True)
            for r in resolvers:
                if hasattr(r, 'domains') and r.domains:
                    for dom in r.domains:
                        if '*' not in dom:
                            hosts.add(dom.lower())
        except Exception as e:
            print(f"[ENGINE] Error gathering from resolveurl: {e}")

    try:
        scrape_sources_path = os.path.join(PROJECT_ROOT, 'modules', 'scrape_sources.py')
        if os.path.exists(scrape_sources_path):
            with open(scrape_sources_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            matches = re.findall(r'(\w+(?:_domains|_working_domains|_redir_domains))\s*=\s*\[(.*?)\]', content, re.DOTALL)
            for var_name, list_content in matches:
                found = re.findall(r"['\"]([^'\"]+)['\"]", list_content)
                for dom in found:
                    hosts.add(dom.lower())
    except Exception as e:
        print(f"[ENGINE] Error scanning scrape_sources.py: {e}")

    return sorted(list(hosts))


def gather_provider_pack_hosts():
    hosts = set()
    if not os.path.exists(SOURCES_PATH):
        return []
    for pack in os.listdir(SOURCES_PATH):
        pack_dir = os.path.join(SOURCES_PATH, pack)
        if not os.path.isdir(pack_dir):
            continue
        for file in os.listdir(pack_dir):
            if not (file.endswith('.py') and not file.startswith('__')):
                continue
            filepath = os.path.join(pack_dir, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                matches = re.findall(r"self\.domains\s*=\s*\[([^\]]*)\]", content, re.DOTALL)
                for list_content in matches:
                    found = re.findall(r"['\"]([^'\"]+)['\"]", list_content)
                    for d in found:
                        if d and '*' not in d:
                            hosts.add(d.lower())
            except Exception as e:
                print(f"[ENGINE] Error scanning {pack}/{file}: {e}")
    return sorted(list(hosts))


def get_default_whitelist():
    hosts = list(DEFAULT_WHITELIST)
    if resolveurl and hasattr(resolveurl, 'relevant_resolvers'):
        try:
            resolvers = resolveurl.relevant_resolvers(order_matters=True)
            for r in resolvers:
                if not '*' in r.domains:
                    for d in r.domains:
                        d_low = d.lower()
                        if d_low not in hosts:
                            hosts.append(d_low)
        except: pass
    for h in gather_provider_pack_hosts():
        if h not in hosts:
            hosts.append(h)
    return sorted(hosts)

def load_config():
    default_config = {
        "timeout_mode": "Both",
        "global_timeout": 30,
        "per_source_timeout": 15,
        "use_only_whitelisted_hosts": True,
        "whitelisted_hosts": get_default_whitelist(),
        "subtitles_languages": "English",
        "subtitles_limit": 20,
        "addic7ed_enabled": True,
        "bsplayer_enabled": False,
        "opensubtitles_enabled": True,
        "podnadpisi_enabled": False,
        "subdl_enabled": True,
        "subsource_enabled": True,
        "opensubtitles_username": "",
        "opensubtitles_password": "",
        "opensubtitles_org_username": "",
        "opensubtitles_org_password": "",
        "subdl_apikey": "",
        "subsource_apikey": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_cfg = json.load(f)
                default_config.update(user_cfg)
        except Exception: pass
    return default_config

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=4)

GLOBAL_CONFIG = load_config()

class UniversalScraper:
    def __init__(self, enabled_packs):
        self.enabled_packs = enabled_packs
        self.sources = []
        self.provider_instances = {}

        cfg = GLOBAL_CONFIG
        use_only = cfg.get("use_only_whitelisted_hosts", True)

        if use_only:
            self.hostDict = cfg.get("whitelisted_hosts", [])
            self.hostDict = list(set([h.lower() for h in self.hostDict]))
        else:
            self.hostDict = []

        provider_set = set(gather_provider_pack_hosts())
        self.provider_hosts = [h for h in self.hostDict if h in provider_set]

    def getSources(self, title, year, imdb, tmdb, tvdb='0', season=None, episode=None, tvshowtitle=None, premiered='0', progress_callback=None):
        print(f"\n[ENGINE] Starting Universal Scrape for: {title} ({year})")
        providers = []

        for pack in self.enabled_packs:
            pack_dir = os.path.join(SOURCES_PATH, pack)
            if not os.path.exists(pack_dir): continue
            
            for file in os.listdir(pack_dir):
                if file.endswith('.py') and not file.startswith('__'):
                    mod_name = f"sources.{pack}.{file[:-3]}"
                    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(pack_dir, file))
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = mod
                    try:
                        spec.loader.exec_module(mod)
                        if hasattr(mod, 'source'):
                            instance = mod.source()
                            instance_domains = [d.lower() for d in (getattr(instance, 'domains', None) or [])]
                            if self.hostDict and instance_domains:
                                if not any(d in self.provider_hosts for d in instance_domains):
                                    print(f"[ENGINE] Skipping {pack}/{file}: no whitelisted domains in {instance_domains}")
                                    continue
                            providers.append((pack, file[:-3], instance))
                            self.provider_instances[f"{pack}_{file[:-3]}"] = instance
                    except Exception as e:
                        print(f"[ENGINE] Failed to load {pack}/{file}: {e}")

        content = 'movie' if tvshowtitle is None else 'episode'
        threads = []
        aliases_str = "[]" 
        
        active_providers = []
        for pack_name, name, provider in providers:
            if content == 'movie' and hasattr(provider, 'movie'):
                active_providers.append((pack_name, name, provider))
            elif content == 'episode' and hasattr(provider, 'tvshow'):
                active_providers.append((pack_name, name, provider))

        total_providers = len(active_providers)
        
        if progress_callback:
            progress_callback(None, None, 'started', [], 0, total_providers)

        completed_lock = threading.Lock()
        completed = 0

        def local_callback(pack_name, name, status, found_results):
            nonlocal completed
            with completed_lock:
                completed += 1
                curr = completed
            if progress_callback:
                progress_callback(pack_name, name, status, found_results, curr, total_providers)

        for pack_name, name, provider in active_providers:
            if content == 'movie':
                threads.append(threading.Thread(target=self.worker, args=(
                    provider, content, title, title, aliases_str, year, imdb, tmdb, None, None, None, None, name, pack_name, local_callback
                )))
            elif content == 'episode':
                threads.append(threading.Thread(target=self.worker, args=(
                    provider, content, title, title, aliases_str, year, imdb, tmdb, tvdb, season, episode, premiered, name, pack_name, local_callback
                )))

        [t.start() for t in threads]
        mode = GLOBAL_CONFIG.get('timeout_mode', 'Both')
        global_to = GLOBAL_CONFIG.get('global_timeout', 30)
        per_source_to = GLOBAL_CONFIG.get('per_source_timeout', 15)
        max_wait = global_to if mode in ["Global", "Both"] else (per_source_to + 5)
        print(f"[ENGINE] Timeout Mode: {mode} (Max Wait: {max_wait}s)")
        start_time = time.time()
        while any(t.is_alive() for t in threads):
            if time.time() - start_time > max_wait: 
                print("\n[ENGINE] Time limit reached! Returning gathered sources.")
                break
            alive = len([t for t in threads if t.is_alive()])
            print(f"[ENGINE] Waiting for {alive} providers...", end='\r')
            time.sleep(0.5)

        quality_map = {'4k': 0, '1080p': 1, '720p': 2, 'hd': 2, 'sd': 3, 'cam': 4, 'scr': 4}
        for s in self.sources:
            s['q_sort'] = quality_map.get(str(s.get('quality')).lower(), 3)
        self.sources.sort(key=lambda x: x['q_sort'])

        for s in self.sources:
            if 'source' not in s and 'host' in s: s['source'] = s['host']
            if 'provider' not in s: s['provider'] = '[Unknown]'

        return self.sources

    def worker(self, provider, content, title, localtitle, aliases, year, imdb, tmdb, tvdb, season, episode, premiered, name, pack_name, callback=None):
        print(f"[ENGINE] Scraping from: {pack_name} -> {name}")
        results = []
        status = "failed"
        try:
            if content == 'movie':
                sig = inspect.signature(provider.movie)
                if 'tmdb' in sig.parameters:
                    url = provider.movie(imdb, tmdb, title, localtitle, aliases, year)
                else:
                    url = provider.movie(imdb, title, localtitle, aliases, year)
            else:
                sig = inspect.signature(provider.tvshow)
                if 'tmdb' in sig.parameters:
                    url = provider.tvshow(imdb, tmdb, tvdb, title, localtitle, aliases, year)
                else:
                    url = provider.tvshow(imdb, tvdb, title, localtitle, aliases, year)
                
                if url and hasattr(provider, 'episode'):
                    ep_sig = inspect.signature(provider.episode)
                    if 'tmdb' in ep_sig.parameters:
                        url = provider.episode(url, imdb, tmdb, tvdb, title, premiered, season, episode)
                    else:
                        url = provider.episode(url, imdb, tvdb, title, premiered, season, episode)

            if url:
                sources_sig = inspect.signature(provider.sources)
                if 'hostprDict' in sources_sig.parameters:
                    results = provider.sources(url, self.hostDict, [])
                else:
                    results = provider.sources(url, self.hostDict)

                if results:
                    status = "success"
                    for res in results:
                        res.setdefault('provider', f"[{pack_name}] {name}")
                        res.setdefault('direct', False)
                        res['provider_key'] = f"{pack_name}_{name}"
                    self.sources.extend(results)
                else:
                    status = "no sources"
                    results = []
            else:
                status = "no url"
                results = []
        except Exception as e:
            print(f"[ENGINE] Error in worker for {name}: {e}")
            traceback.print_exc()
            status = f"error: {str(e)}"
            results = []
        finally:
            if callback:
                try:
                    callback(pack_name, name, status, results)
                except Exception as cb_err:
                    print(f"[ENGINE] Error calling progress callback: {cb_err}")

    def resolveSource(self, source_data):
        url = source_data.get('url')
        provider_key = source_data.get('provider_key')

        if provider_key in self.provider_instances:
            provider = self.provider_instances[provider_key]
            if hasattr(provider, 'resolve'):
                try: url = provider.resolve(url)
                except: pass

        if not url: return None

        try:
            import modules.scrape_sources as scrape_sources
            url = scrape_sources.prepare_link(url)
        except Exception: pass

        if not url: return None

        if resolveurl and hasattr(resolveurl, 'HostedMediaFile'):
            try:
                if resolveurl.HostedMediaFile(url):
                    resolved = resolveurl.resolve(url)
                    if resolved: return resolved
            except: pass
            
        return url

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QListWidget, 
                             QListWidgetItem, QLabel, QProgressBar, QMessageBox, 
                             QSplitter, QDialog, QCheckBox, QScrollArea, QComboBox, 
                             QTimeEdit, QFormLayout, QFrame, QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTime
from PyQt6.QtGui import QPixmap, QImage

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Engine & Provider Settings")
        self.resize(550, 650)
        self.layout = QVBoxLayout(self)
        self.cfg = GLOBAL_CONFIG
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        self.tab_general = QWidget()
        self.layout_general = QVBoxLayout(self.tab_general)
        self.form_layout = QFormLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Global", "Per-Source", "Both"])
        self.combo_mode.setCurrentText(self.cfg.get("timeout_mode", "Both"))
        self.combo_mode.currentTextChanged.connect(self.update_ui_state)
        self.time_global = QTimeEdit()
        self.time_global.setDisplayFormat("mm:ss")
        g_sec = self.cfg.get("global_timeout", 30)
        self.time_global.setTime(QTime(0, g_sec // 60, g_sec % 60))
        self.time_source = QTimeEdit()
        self.time_source.setDisplayFormat("mm:ss")
        s_sec = self.cfg.get("per_source_timeout", 15)
        self.time_source.setTime(QTime(0, s_sec // 60, s_sec % 60))
        self.form_layout.addRow("Timeout Mode:", self.combo_mode)
        self.form_layout.addRow("Global Timeout:", self.time_global)
        self.form_layout.addRow("Per-Source Timeout:", self.time_source)
        self.layout_general.addLayout(self.form_layout)
        self.update_ui_state(self.combo_mode.currentText())
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout_general.addWidget(line)
        self.layout_general.addWidget(QLabel("<b>Provider Packs</b>"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.vbox = QVBoxLayout(content)
        self.checkboxes = {}
        packs = [d for d in os.listdir(SOURCES_PATH) if os.path.isdir(os.path.join(SOURCES_PATH, d))]
        if not packs:
            self.vbox.addWidget(QLabel("No provider packs found in sources/ directory."))
        else:
            for pack in packs:
                cb = QCheckBox(f"Enable '{pack}'")
                cb.setChecked(self.cfg.get(f"pack_{pack}", True))
                self.checkboxes[f"pack_{pack}"] = cb
                self.vbox.addWidget(cb)
        self.vbox.addStretch()
        scroll.setWidget(content)
        self.layout_general.addWidget(scroll)
        self.tabs.addTab(self.tab_general, "General Settings")
        
        self.tab_hosts = QWidget()
        self.layout_hosts = QVBoxLayout(self.tab_hosts)
        self.cb_use_only = QCheckBox("Use only these hosts")
        self.cb_use_only.setChecked(self.cfg.get("use_only_whitelisted_hosts", True))
        self.cb_use_only.stateChanged.connect(self.update_hosts_enabled_state)
        self.layout_hosts.addWidget(self.cb_use_only)
        search_layout = QHBoxLayout()
        self.host_search = QLineEdit()
        self.host_search.setPlaceholderText("Search hosts...")
        self.host_search.textChanged.connect(self.filter_hosts)
        search_layout.addWidget(self.host_search)
        self.btn_all = QPushButton("Select All")
        self.btn_all.clicked.connect(self.select_all_hosts)
        self.btn_none = QPushButton("Clear All")
        self.btn_none.clicked.connect(self.clear_all_hosts)
        self.btn_default = QPushButton("Reset to Defaults")
        self.btn_default.clicked.connect(self.reset_hosts_to_default)
        search_layout.addWidget(self.btn_all)
        search_layout.addWidget(self.btn_none)
        search_layout.addWidget(self.btn_default)
        self.layout_hosts.addLayout(search_layout)
        self.scroll_hosts = QScrollArea()
        self.scroll_hosts.setWidgetResizable(True)
        content_hosts = QWidget()
        self.vbox_hosts = QVBoxLayout(content_hosts)
        self.host_checkboxes = {}
        resolveurl_set = set(gather_resolveurl_hosts())
        provider_set = set(gather_provider_pack_hosts())
        all_hosts = sorted(resolveurl_set | provider_set)
        whitelisted = self.cfg.get("whitelisted_hosts", [])
        whitelisted_low = set(w.lower() for w in whitelisted)

        resolveurl_only = [h for h in all_hosts if h in resolveurl_set]
        provider_only = [h for h in all_hosts if h in provider_set and h not in resolveurl_set]

        section_resolveurl = self._build_host_section("ResolveURL Hosts", resolveurl_only, whitelisted_low)
        section_provider = self._build_host_section("Provider Pack Hosts", provider_only, whitelisted_low)
        self.vbox_hosts.addWidget(section_resolveurl)
        self.vbox_hosts.addWidget(section_provider)
        self.vbox_hosts.addStretch()
        self.scroll_hosts.setWidget(content_hosts)
        self.layout_hosts.addWidget(self.scroll_hosts)
        self.tabs.addTab(self.tab_hosts, "Provider Whitelist")
        self.update_hosts_enabled_state()

        self.tab_subtitles = QWidget()
        self.layout_subtitles = QVBoxLayout(self.tab_subtitles)
        sub_scroll = QScrollArea()
        sub_scroll.setWidgetResizable(True)
        sub_content = QWidget()
        self.form_subtitles = QFormLayout(sub_content)
        
        self.edit_sub_langs = QLineEdit()
        self.edit_sub_langs.setPlaceholderText("e.g. English, Spanish")
        self.edit_sub_langs.setText(self.cfg.get("subtitles_languages", "English"))
        self.form_subtitles.addRow("Languages (comma separated):", self.edit_sub_langs)
        
        self.combo_sub_limit = QComboBox()
        self.combo_sub_limit.addItems(["10", "20", "30", "50", "100"])
        self.combo_sub_limit.setCurrentText(str(self.cfg.get("subtitles_limit", 20)))
        self.form_subtitles.addRow("Subtitles Limit:", self.combo_sub_limit)
        
        self.form_subtitles.addRow(QLabel("<b>Subtitle Services</b>"), QLabel(""))
        
        self.cb_addic7ed = QCheckBox("Enable Addic7ed (TV only)")
        self.cb_addic7ed.setChecked(self.cfg.get("addic7ed_enabled", True))
        self.form_subtitles.addRow("", self.cb_addic7ed)
        
        self.cb_bsplayer = QCheckBox("Enable BSPlayer (requires hashes)")
        self.cb_bsplayer.setChecked(self.cfg.get("bsplayer_enabled", False))
        self.form_subtitles.addRow("", self.cb_bsplayer)
        
        self.cb_opensubtitles = QCheckBox("Enable OpenSubtitles.com")
        self.cb_opensubtitles.setChecked(self.cfg.get("opensubtitles_enabled", True))
        self.form_subtitles.addRow("", self.cb_opensubtitles)
        
        self.cb_opensubtitles_org = QCheckBox("Enable OpenSubtitles.org")
        self.cb_opensubtitles_org.setChecked(self.cfg.get("opensubtitles_org_enabled", False))
        self.form_subtitles.addRow("", self.cb_opensubtitles_org)
        
        self.cb_podnadpisi = QCheckBox("Enable Podnadpisi")
        self.cb_podnadpisi.setChecked(self.cfg.get("podnadpisi_enabled", False))
        self.form_subtitles.addRow("", self.cb_podnadpisi)
        
        self.cb_subdl = QCheckBox("Enable SubDL")
        self.cb_subdl.setChecked(self.cfg.get("subdl_enabled", True))
        self.form_subtitles.addRow("", self.cb_subdl)
        
        self.cb_subsource = QCheckBox("Enable Subsource")
        self.cb_subsource.setChecked(self.cfg.get("subsource_enabled", True))
        self.form_subtitles.addRow("", self.cb_subsource)
        
        self.form_subtitles.addRow(QLabel("<b>Account Settings / API Keys</b>"), QLabel(""))
        
        self.edit_opensub_user = QLineEdit()
        self.edit_opensub_user.setText(self.cfg.get("opensubtitles_username", ""))
        self.edit_opensub_user.setPlaceholderText("Username (not email)")
        self.form_subtitles.addRow("OpenSubtitles Username:", self.edit_opensub_user)
        
        self.edit_opensub_pass = QLineEdit()
        self.edit_opensub_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_opensub_pass.setText(self.cfg.get("opensubtitles_password", ""))
        self.edit_opensub_pass.setPlaceholderText("Password")
        self.form_subtitles.addRow("OpenSubtitles Password:", self.edit_opensub_pass)
        
        self.edit_opensub_org_user = QLineEdit()
        self.edit_opensub_org_user.setText(self.cfg.get("opensubtitles_org_username", ""))
        self.edit_opensub_org_user.setPlaceholderText("Username")
        self.form_subtitles.addRow("OpenSubtitles.org Username:", self.edit_opensub_org_user)
        
        self.edit_opensub_org_pass = QLineEdit()
        self.edit_opensub_org_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_opensub_org_pass.setText(self.cfg.get("opensubtitles_org_password", ""))
        self.edit_opensub_org_pass.setPlaceholderText("Password")
        self.form_subtitles.addRow("OpenSubtitles.org Password:", self.edit_opensub_org_pass)
        
        self.edit_subdl_key = QLineEdit()
        self.edit_subdl_key.setText(self.cfg.get("subdl_apikey", ""))
        self.edit_subdl_key.setPlaceholderText("API Key")
        self.form_subtitles.addRow("SubDL API Key:", self.edit_subdl_key)
        
        self.edit_subsource_key = QLineEdit()
        self.edit_subsource_key.setText(self.cfg.get("subsource_apikey", ""))
        self.edit_subsource_key.setPlaceholderText("API Key")
        self.form_subtitles.addRow("Subsource API Key:", self.edit_subsource_key)
        
        sub_scroll.setWidget(sub_content)
        self.layout_subtitles.addWidget(sub_scroll)
        self.tabs.addTab(self.tab_subtitles, "Subtitles Settings")
        
        btn_save = QPushButton("Save && Close")
        btn_save.clicked.connect(self.save_and_close)
        self.layout.addWidget(btn_save)

    def _build_host_section(self, title, hosts, whitelisted_low):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet('''
            QFrame {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QFrame:disabled {
                background-color: #1f1f1f;
                border-color: #2a2a2a;
            }
        ''')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(4)
        header = QLabel(f"<b>{title}</b>")
        header.setStyleSheet("color: #0e639c; padding-bottom: 2px; background: transparent; border: none;")
        layout.addWidget(header)
        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(2)
        for h in hosts:
            cb = QCheckBox(h)
            cb.setChecked(h in whitelisted_low)
            cb.stateChanged.connect(self.on_host_checkbox_changed)
            self.host_checkboxes[h] = cb
            inner.addWidget(cb)
        layout.addLayout(inner)
        return frame

    def update_hosts_enabled_state(self):
        is_checked = self.cb_use_only.isChecked()
        self.host_search.setEnabled(is_checked)
        self.btn_all.setEnabled(is_checked)
        self.btn_none.setEnabled(is_checked)
        self.btn_default.setEnabled(is_checked)
        self.scroll_hosts.setEnabled(is_checked)
        if is_checked:
            any_checked = any(cb.isChecked() for cb in self.host_checkboxes.values())
            if not any_checked:
                self.reset_hosts_to_default()

    def filter_hosts(self, text):
        text = text.lower().strip()
        for h, cb in self.host_checkboxes.items():
            cb.setVisible(not text or text in h)

    def select_all_hosts(self):
        for cb in self.host_checkboxes.values():
            cb.blockSignals(True)
            if cb.isVisible():
                cb.setChecked(True)
            cb.blockSignals(False)
        self.on_host_checkbox_changed()

    def clear_all_hosts(self):
        for cb in self.host_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self.on_host_checkbox_changed()

    def reset_hosts_to_default(self):
        default_hosts = get_default_whitelist()
        default_hosts_low = [d.lower() for d in default_hosts]
        for h, cb in self.host_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(h in default_hosts_low)
            cb.blockSignals(False)
        self.on_host_checkbox_changed()

    def on_host_checkbox_changed(self):
        any_checked = any(cb.isChecked() for cb in self.host_checkboxes.values())
        
        if any_checked:
            self.cb_use_only.blockSignals(True)
            self.cb_use_only.setChecked(True)
            self.cb_use_only.blockSignals(False)
            
        is_checked = self.cb_use_only.isChecked()
        self.host_search.setEnabled(is_checked)
        self.btn_all.setEnabled(is_checked)
        self.btn_none.setEnabled(is_checked)
        self.btn_default.setEnabled(is_checked)
        self.scroll_hosts.setEnabled(is_checked)

    def update_ui_state(self, mode):
        lbl_global = self.form_layout.labelForField(self.time_global)
        lbl_source = self.form_layout.labelForField(self.time_source)

        if mode == "Global":
            self.time_global.setVisible(True)
            if lbl_global: lbl_global.setVisible(True)
            self.time_source.setVisible(False)
            if lbl_source: lbl_source.setVisible(False)
        elif mode == "Per-Source":
            self.time_global.setVisible(False)
            if lbl_global: lbl_global.setVisible(False)
            self.time_source.setVisible(True)
            if lbl_source: lbl_source.setVisible(True)
        else:
            self.time_global.setVisible(True)
            if lbl_global: lbl_global.setVisible(True)
            self.time_source.setVisible(True)
            if lbl_source: lbl_source.setVisible(True)

    def save_and_close(self):
        self.cfg["timeout_mode"] = self.combo_mode.currentText()
        g_time = self.time_global.time()
        self.cfg["global_timeout"] = g_time.minute() * 60 + g_time.second()
        s_time = self.time_source.time()
        self.cfg["per_source_timeout"] = s_time.minute() * 60 + s_time.second()
        for pack_key, cb in self.checkboxes.items():
            self.cfg[pack_key] = cb.isChecked()

        self.cfg["use_only_whitelisted_hosts"] = self.cb_use_only.isChecked()
        self.cfg["whitelisted_hosts"] = [h for h, cb in self.host_checkboxes.items() if cb.isChecked()]
        
        self.cfg["subtitles_languages"] = self.edit_sub_langs.text()
        self.cfg["subtitles_limit"] = int(self.combo_sub_limit.currentText())
        self.cfg["addic7ed_enabled"] = self.cb_addic7ed.isChecked()
        self.cfg["bsplayer_enabled"] = self.cb_bsplayer.isChecked()
        self.cfg["opensubtitles_enabled"] = self.cb_opensubtitles.isChecked()
        self.cfg["opensubtitles_org_enabled"] = self.cb_opensubtitles_org.isChecked()
        self.cfg["podnadpisi_enabled"] = self.cb_podnadpisi.isChecked()
        self.cfg["subdl_enabled"] = self.cb_subdl.isChecked()
        self.cfg["subsource_enabled"] = self.cb_subsource.isChecked()
        self.cfg["opensubtitles_username"] = self.edit_opensub_user.text()
        self.cfg["opensubtitles_password"] = self.edit_opensub_pass.text()
        self.cfg["opensubtitles_org_username"] = self.edit_opensub_org_user.text()
        self.cfg["opensubtitles_org_password"] = self.edit_opensub_org_pass.text()
        self.cfg["subdl_apikey"] = self.edit_subdl_key.text()
        self.cfg["subsource_apikey"] = self.edit_subsource_key.text()
        
        save_config(self.cfg)
        global GLOBAL_CONFIG
        GLOBAL_CONFIG = self.cfg
        self.accept()

class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    def __init__(self, query):
        super().__init__()
        self.query = query
    def run(self):
        try:
            api_key = "f5608fba6ab49e9985828b35d5653321"
            url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={self.query.replace(' ', '+')}"
            results = requests.get(url).json().get('results', [])
            filtered = [r for r in results if r.get('media_type') in ['movie', 'tv']]
            self.results_ready.emit(filtered)
        except: self.results_ready.emit([])

class MovieItemWidget(QWidget):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5)
        self.poster = QLabel(); self.poster.setFixedSize(80, 120); self.poster.setStyleSheet("background: #2d2d2d; border-radius: 4px;"); self.poster.setScaledContents(True); layout.addWidget(self.poster)
        info = QVBoxLayout()
        m_type = item.get('media_type', 'movie').upper()
        badge = f"<span style='color: #0e639c; font-weight: bold;'>[{m_type}]</span> "
        year = (item.get('release_date') or item.get('first_air_date') or '0000')[:4]
        title_text = f"{badge}<b style='color: #e0e0e0;'>{item.get('title') or item.get('name')} ({year})</b>"
        info.addWidget(QLabel(title_text))
        blurb = QLabel(item.get('overview', '...')); blurb.setWordWrap(True); blurb.setStyleSheet("color: #999; font-size: 11px;"); info.addWidget(blurb); layout.addLayout(info)
        if item.get('poster_path'):
            self.dl = PosterDownloader(f"https://image.tmdb.org/t/p/w185{item['poster_path']}")
            self.dl.finished.connect(lambda img: self.poster.setPixmap(QPixmap.fromImage(img))); self.dl.start()

class PosterDownloader(QThread):
    finished = pyqtSignal(QImage)
    def __init__(self, url): super().__init__(); self.url = url
    def run(self):
        try: data = requests.get(self.url, timeout=5).content; img = QImage(); img.loadFromData(data); self.finished.emit(img)
        except: pass

class TvDetailsFetcher(QThread):
    details_ready = pyqtSignal(dict)
    def __init__(self, tv_id, api_key):
        super().__init__()
        self.tv_id = tv_id
        self.api_key = api_key
    def run(self):
        try:
            url = f"https://api.themoviedb.org/3/tv/{self.tv_id}?api_key={self.api_key}"
            res = requests.get(url).json()
            self.details_ready.emit(res)
        except:
            self.details_ready.emit({})

class TvEpisodesFetcher(QThread):
    episodes_ready = pyqtSignal(list)
    def __init__(self, tv_id, season_number, api_key):
        super().__init__()
        self.tv_id = tv_id
        self.season_number = season_number
        self.api_key = api_key
    def run(self):
        try:
            url = f"https://api.themoviedb.org/3/tv/{self.tv_id}/season/{self.season_number}?api_key={self.api_key}"
            res = requests.get(url).json().get('episodes', [])
            self.episodes_ready.emit(res)
        except:
            self.episodes_ready.emit([])

class TvShowSelectionDialog(QDialog):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.api_key = "f5608fba6ab49e9985828b35d5653321"
        self.selected_season = None
        self.selected_episode = None
        self.selected_premiered = None
        
        self.setWindowTitle(f"Select Episode - {item.get('name')}")
        self.resize(550, 450)
        
        self.layout = QVBoxLayout(self)
        
        self.title_label = QLabel(f"<h2>{item.get('name')}</h2>")
        self.title_label.setStyleSheet("color: #e0e0e0;")
        self.layout.addWidget(self.title_label)
        
        season_layout = QHBoxLayout()
        season_layout.addWidget(QLabel("Season:"))
        self.season_combo = QComboBox()
        self.season_combo.currentIndexChanged.connect(self.on_season_changed)
        season_layout.addWidget(self.season_combo)
        self.layout.addLayout(season_layout)
        
        self.layout.addWidget(QLabel("Episodes:"))
        self.episodes_list = QListWidget()
        self.episodes_list.itemSelectionChanged.connect(self.on_episode_selection_changed)
        self.episodes_list.itemDoubleClicked.connect(self.on_episode_double_clicked)
        self.layout.addWidget(self.episodes_list)
        
        self.status_label = QLabel("Loading seasons...")
        self.status_label.setStyleSheet("color: #aaa;")
        self.layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("Scrape Episode")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        self.layout.addLayout(btn_layout)
        
        self.details_fetcher = TvDetailsFetcher(self.item['id'], self.api_key)
        self.details_fetcher.details_ready.connect(self.on_details_ready)
        self.details_fetcher.start()
        
    def on_details_ready(self, details):
        if not details or 'seasons' not in details:
            self.status_label.setText("Failed to load show details.")
            return
        
        self.seasons = [s for s in details['seasons'] if s.get('season_number') is not None]
        self.seasons.sort(key=lambda x: x['season_number'])
        
        self.season_combo.blockSignals(True)
        self.season_combo.clear()
        for s in self.seasons:
            name = s.get('name') or f"Season {s['season_number']}"
            ep_count = s.get('episode_count', 0)
            self.season_combo.addItem(f"{name} ({ep_count} Episodes)", s['season_number'])
        self.season_combo.blockSignals(False)
        
        if self.seasons:
            self.status_label.setText("Seasons loaded. Select a season.")
            self.on_season_changed(0)
        else:
            self.status_label.setText("No seasons found.")
            
    def on_season_changed(self, index):
        if index < 0 or index >= self.season_combo.count():
            return
        
        season_number = self.season_combo.itemData(index)
        self.episodes_list.clear()
        self.btn_select.setEnabled(False)
        self.status_label.setText(f"Loading episodes for Season {season_number}...")
        
        self.ep_fetcher = TvEpisodesFetcher(self.item['id'], season_number, self.api_key)
        self.ep_fetcher.episodes_ready.connect(self.on_episodes_ready)
        self.ep_fetcher.start()
        
    def on_episodes_ready(self, episodes):
        self.episodes = episodes
        if not episodes:
            self.status_label.setText("No episodes found or failed to load episodes.")
            return
            
        self.episodes_list.clear()
        for ep in episodes:
            ep_num = ep.get('episode_number', 0)
            name = ep.get('name') or f"Episode {ep_num}"
            air_date = ep.get('air_date') or "Unknown Date"
            item_text = f"Episode {ep_num}: {name} ({air_date})"
            
            li = QListWidgetItem(item_text)
            li.setData(Qt.ItemDataRole.UserRole, ep)
            self.episodes_list.addItem(li)
            
        self.status_label.setText("Select an episode to scrape.")
        
    def on_episode_selection_changed(self):
        selected = self.episodes_list.selectedItems()
        self.btn_select.setEnabled(len(selected) > 0)
        
    def on_episode_double_clicked(self, item):
        self.accept()
        
    def accept(self):
        selected = self.episodes_list.selectedItems()
        if not selected:
            return
        ep_data = selected[0].data(Qt.ItemDataRole.UserRole)
        self.selected_season = self.season_combo.currentData()
        self.selected_episode = ep_data.get('episode_number')
        self.selected_premiered = ep_data.get('air_date') or '0'
        super().accept()

class ScrapeWorker(QThread):
    sources_ready = pyqtSignal(list)
    sources_found = pyqtSignal(list)
    progress_updated = pyqtSignal(int, int, str)
    
    def __init__(self, item, enabled_packs, season=None, episode=None, premiered=None): 
        super().__init__()
        self.item = item
        self.enabled_packs = enabled_packs
        self.season = season
        self.episode = episode
        self.premiered = premiered

    def run(self):
        try:
            tmdb_id = str(self.item['id'])
            api_key = "f5608fba6ab49e9985828b35d5653321"
            
            def local_progress_callback(pack_name, name, status, found_results, current_completed, total_count):
                if status == 'started':
                    self.progress_updated.emit(0, total_count, f"Starting search across {total_count} providers...")
                else:
                    count = len(found_results) if found_results else 0
                    msg = f"Scraped {pack_name} -> {name}: {status.upper()}"
                    if count > 0:
                        msg += f" ({count} sources found)"
                        self.sources_found.emit(found_results)
                    self.progress_updated.emit(current_completed, total_count, msg)

            if self.season is not None and self.episode is not None:
                ext_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={api_key}"
                imdb_id = requests.get(ext_url).json().get('imdb_id', '0')
                scraper = UniversalScraper(self.enabled_packs)
                file_sources = scraper.getSources(
                    title=self.item.get('name'), 
                    year=self.item.get('first_air_date', '0000')[:4], 
                    imdb=imdb_id, 
                    tmdb=tmdb_id,
                    season=str(self.season),
                    episode=str(self.episode),
                    tvshowtitle=self.item.get('name'),
                    premiered=self.premiered or '0',
                    progress_callback=local_progress_callback
                )
            else:
                ext_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids?api_key={api_key}"
                imdb_id = requests.get(ext_url).json().get('imdb_id', '0')
                scraper = UniversalScraper(self.enabled_packs)
                file_sources = scraper.getSources(
                    title=self.item['title'], 
                    year=self.item.get('release_date', '0000')[:4], 
                    imdb=imdb_id, 
                    tmdb=tmdb_id,
                    progress_callback=local_progress_callback
                )
            self.sources_ready.emit(file_sources)
        except Exception as e:
            print(f"Error scraping: {e}")
            traceback.print_exc()
            self.sources_ready.emit([])

class ResolveWorker(QThread):
    resolved = pyqtSignal(str)
    failed = pyqtSignal(str)
    
    def __init__(self, source_data, enabled_packs):
        super().__init__()
        self.source_data = source_data
        self.enabled_packs = enabled_packs
        
    def run(self):
        try:
            scraper = UniversalScraper(self.enabled_packs)
            final = scraper.resolveSource(self.source_data)
            if final:
                self.resolved.emit(final)
            else:
                self.failed.emit("Could not resolve stream.")
        except Exception as e:
            self.failed.emit(str(e))

class SubtitlesScrapeWorker(QThread):
    subtitles_ready = pyqtSignal(list)
    
    def __init__(self, item, settings, season=None, episode=None):
        super().__init__()
        self.item = item
        self.settings = settings
        self.season = season
        self.episode = episode
        
    def run(self):
        try:
            import subtitles.manager as sub_manager
            
            tmdb_id = str(self.item['id'])
            api_key = "f5608fba6ab49e9985828b35d5653321"
            
            if self.season is not None and self.episode is not None:
                ext_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={api_key}"
                imdb_id = requests.get(ext_url).json().get('imdb_id', '0')
                title = self.item.get('name')
                year = self.item.get('first_air_date', '0000')[:4]
                tvshow = self.item.get('name')
            else:
                ext_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids?api_key={api_key}"
                imdb_id = requests.get(ext_url).json().get('imdb_id', '0')
                title = self.item.get('title')
                year = self.item.get('release_date', '0000')[:4]
                tvshow = None
                
            results = sub_manager.search_subtitles(
                imdb_id=imdb_id,
                title=title,
                year=year,
                season=self.season,
                episode=self.episode,
                tvshow=tvshow,
                settings=self.settings
            )
            self.subtitles_ready.emit(results or [])
        except Exception as e:
            print(f"Error scraping subtitles: {e}")
            traceback.print_exc()
            self.subtitles_ready.emit([])

class SubtitleDownloadWorker(QThread):
    downloaded = pyqtSignal(str)
    failed = pyqtSignal(str)
    
    def __init__(self, service_name, action_args, settings):
        super().__init__()
        self.service_name = service_name
        self.action_args = action_args
        self.settings = settings
        
    def run(self):
        try:
            import subtitles.manager as sub_manager
            filepath = sub_manager.download_subtitle(
                self.service_name,
                self.action_args,
                settings=self.settings
            )
            if filepath:
                self.downloaded.emit(filepath)
            else:
                self.failed.emit("Failed to download or save subtitle.")
        except Exception as e:
            self.failed.emit(str(e))

class UniversalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Scraper Client")
        self.resize(1100, 800)
        self.setStyleSheet('''
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: "Segoe UI", "Helvetica", sans-serif;
            }
            QLineEdit {
                padding: 8px 12px;
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 6px;
                selection-background-color: #0e639c;
            }
            QLineEdit:hover {
                border-color: #666;
                background-color: #333;
            }
            QLineEdit:focus {
                border-color: #0e639c;
            }
            QLineEdit:disabled {
                background-color: #252525;
                color: #777;
            }
            QPushButton {
                padding: 8px 18px;
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
                border-color: #3a3a3a;
            }
            QPushButton#btn_search {
                background-color: #e8870e;
                color: #111;
                border-color: #f39c12;
            }
            QPushButton#btn_search:hover {
                background-color: #f5a623;
                border-color: #f5a623;
            }
            QPushButton#btn_settings {
                background-color: #3a3a3a;
                border-color: #555;
            }
            QPushButton#btn_settings:hover {
                background-color: #4a4a4a;
                border-color: #777;
            }
            QComboBox {
                padding: 6px 10px;
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 6px;
            }
            QComboBox:hover {
                border-color: #666;
                background-color: #333;
            }
            QComboBox::drop-down {
                width: 20px;
                border: none;
                background-color: #3a3a3a;
            }
            QComboBox::down-arrow {
                image: url(resources/down-arrow.svg);
            }
            QComboBox::drop-down:hover {
                background-color: #555;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #0e639c;
                border: 1px solid #444;
            }
            QTimeEdit {
                padding: 6px 10px;
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 6px;
            }
            QTimeEdit:hover {
                border-color: #666;
                background-color: #333;
            }
            QTimeEdit::up-button,
            QTimeEdit::down-button {
                width: 18px;
                border: none;
            }
            QTimeEdit::up-button:hover,
            QTimeEdit::down-button:hover {
                background-color: #555;
            }
            QTimeEdit::up-arrow {
                image: url(resources/up-arrow.svg);
                width: 8px;
                height: 8px;
            }
            QTimeEdit::down-arrow {
                image: url(resources/down-arrow.svg);
                width: 8px;
                height: 8px;
            }
            QCheckBox {
                spacing: 10px;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #555;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border-color: #888;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #0e639c;
                border-color: #0e639c;
                image: url(resources/checkmark.svg);
            }
            QCheckBox::indicator:disabled {
                background-color: #252525;
                border-color: #3a3a3a;
                image: url(resources/checkmark.svg);
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #1e1e1e;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #aaa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #3a3a3a;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border-color: #555;
                border-bottom: 1px solid #1e1e1e;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
                color: #e0e0e0;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: rgba(14, 99, 156, 0.25);
            }
            QListWidget::item:selected {
                background-color: #0e639c;
                color: #fff;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #444;
                border-radius: 5px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #0e639c;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 10px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #444;
                border-radius: 5px;
                min-width: 20px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QFrame {
                background-color: #3a3a3a;
            }
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 3px;
            }
            QSplitter::handle {
                background-color: #444;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:horizontal:hover {
                background-color: #0e639c;
            }
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QFormLayout {
                min-row-spacing: 8px;
            }
        ''')
        central = QWidget(); self.setCentralWidget(central); self.main_layout = QVBoxLayout(central)
        top_bar = QHBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText("Search Movies or TV Shows...")
        self.input.returnPressed.connect(self.start_search)
        self.btn = QPushButton("Search"); self.btn.setObjectName("btn_search")
        self.btn.clicked.connect(self.start_search)
        self.btn_settings = QPushButton("⚙ Settings"); self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.clicked.connect(self.open_settings)
        top_bar.addWidget(self.input); top_bar.addWidget(self.btn); top_bar.addWidget(self.btn_settings)
        self.main_layout.addLayout(top_bar)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_label = QLabel("<b>1. Search Results</b>")
        self.results_layout.addWidget(self.results_label)
        self.results = QListWidget(); self.results.itemClicked.connect(self.on_selected)
        self.results_layout.addWidget(self.results)
        
        self.sources_widget = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_widget)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_label = QLabel("<b>2. Stream Sources</b>")
        self.sources_layout.addWidget(self.sources_label)
        self.sources_list = QListWidget(); self.sources_list.itemClicked.connect(self.on_resolve)
        self.sources_layout.addWidget(self.sources_list)
        
        self.subtitles_widget = QWidget()
        self.subtitles_layout = QVBoxLayout(self.subtitles_widget)
        self.subtitles_layout.setContentsMargins(0, 0, 0, 0)
        self.subtitles_label = QLabel("<b>3. Subtitles</b>")
        self.subtitles_layout.addWidget(self.subtitles_label)
        self.subtitles_list = QListWidget(); self.subtitles_list.itemClicked.connect(self.on_subtitle_selected)
        self.subtitles_layout.addWidget(self.subtitles_list)
        
        self.splitter.addWidget(self.results_widget)
        self.splitter.addWidget(self.sources_widget)
        self.splitter.addWidget(self.subtitles_widget)
        
        self.splitter.setSizes([400, 400, 400])
        self.main_layout.addWidget(self.splitter)
        
        self.url_panel = QFrame()
        self.url_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.url_panel.setStyleSheet('''
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QLabel {
                font-weight: bold;
                color: #e8870e;
            }
        ''')
        panel_layout = QVBoxLayout(self.url_panel)
        panel_layout.setContentsMargins(15, 10, 15, 10)
        
        stream_row = QHBoxLayout()
        stream_lbl = QLabel("Stream URL:")
        stream_lbl.setFixedWidth(90)
        stream_row.addWidget(stream_lbl)
        self.edit_stream_url = QLineEdit()
        self.edit_stream_url.setReadOnly(True)
        self.edit_stream_url.setPlaceholderText("Resolved stream URL will appear here...")
        self.btn_copy_stream = QPushButton("Copy")
        self.btn_copy_stream.clicked.connect(self.copy_stream_url)
        stream_row.addWidget(self.edit_stream_url)
        stream_row.addWidget(self.btn_copy_stream)
        panel_layout.addLayout(stream_row)
        
        sub_row = QHBoxLayout()
        sub_lbl = QLabel("Subtitle URL:")
        sub_lbl.setFixedWidth(90)
        sub_row.addWidget(sub_lbl)
        self.edit_subtitle_url = QLineEdit()
        self.edit_subtitle_url.setReadOnly(True)
        self.edit_subtitle_url.setPlaceholderText("Downloaded subtitle path will appear here...")
        self.btn_copy_sub = QPushButton("Copy")
        self.btn_copy_sub.clicked.connect(self.copy_subtitle_url)
        sub_row.addWidget(self.edit_subtitle_url)
        sub_row.addWidget(self.btn_copy_sub)
        panel_layout.addLayout(sub_row)
        
        self.main_layout.addWidget(self.url_panel)
        
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 5, 0, 5)
        
        self.progress_status_label = QLabel("Ready")
        self.progress_status_label.setStyleSheet("color: #e8870e; font-weight: bold; font-size: 11px;")
        self.progress_layout.addWidget(self.progress_status_label)
        
        self.progress = QProgressBar()
        self.progress.setStyleSheet('''
            QProgressBar {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                text-align: center;
                color: #e0e0e0;
                font-weight: bold;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 5px;
            }
        ''')
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v of %m Scraped (%p%)")
        self.progress_layout.addWidget(self.progress)
        self.progress_container.setVisible(False)
        self.main_layout.addWidget(self.progress_container)

        self.found_sources = []
        self.is_resolving = False
        self.is_downloading_sub = False

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def get_enabled_packs(self):
        packs = [d for d in os.listdir(SOURCES_PATH) if os.path.isdir(os.path.join(SOURCES_PATH, d))]
        return [p for p in packs if GLOBAL_CONFIG.get(f"pack_{p}", True)]

    def start_search(self):
        self.results.clear(); self.sources_list.clear(); self.subtitles_list.clear()
        self.edit_stream_url.clear(); self.edit_subtitle_url.clear()
        self.btn.setEnabled(False)
        self.search_worker = SearchWorker(self.input.text())
        self.search_worker.results_ready.connect(self.on_search_results)
        self.search_worker.start()

    def on_search_results(self, results):
        self.movie_data = results
        for item in results:
            li = QListWidgetItem(self.results); li.setSizeHint(QSize(400, 130))
            self.results.setItemWidget(li, MovieItemWidget(item))
        self.btn.setEnabled(True)

    def on_selected(self, li):
        idx = self.results.row(li)
        item = self.movie_data[idx]
        self.sources_list.clear()
        self.subtitles_list.clear()
        self.edit_stream_url.clear()
        self.edit_subtitle_url.clear()
        self.found_sources = []
        
        media_type = item.get('media_type', 'movie')
        
        if media_type == 'tv':
            dlg = TvShowSelectionDialog(item, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                season = dlg.selected_season
                episode = dlg.selected_episode
                premiered = dlg.selected_premiered
                
                self.progress_container.setVisible(True)
                self.progress.setRange(0, 0)
                self.progress_status_label.setText("Preparing scrapers...")
                
                enabled_packs = self.get_enabled_packs()
                
                self.worker = ScrapeWorker(item, enabled_packs, season=season, episode=episode, premiered=premiered)
                self.worker.sources_ready.connect(self.on_found)
                self.worker.sources_found.connect(self.on_sources_found)
                self.worker.progress_updated.connect(self.on_scrape_progress)
                self.worker.start()
                
                self.sub_worker = SubtitlesScrapeWorker(item, GLOBAL_CONFIG, season=season, episode=episode)
                self.sub_worker.subtitles_ready.connect(self.on_subtitles_found)
                self.sub_worker.start()
            else:
                self.progress_container.setVisible(False)
        else:
            self.progress_container.setVisible(True)
            self.progress.setRange(0, 0)
            self.progress_status_label.setText("Preparing scrapers...")
            
            enabled_packs = self.get_enabled_packs()
            
            self.worker = ScrapeWorker(item, enabled_packs)
            self.worker.sources_ready.connect(self.on_found)
            self.worker.sources_found.connect(self.on_sources_found)
            self.worker.progress_updated.connect(self.on_scrape_progress)
            self.worker.start()
            
            self.sub_worker = SubtitlesScrapeWorker(item, GLOBAL_CONFIG)
            self.sub_worker.subtitles_ready.connect(self.on_subtitles_found)
            self.sub_worker.start()

    def on_scrape_progress(self, current, total, status_text):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.progress_status_label.setText(status_text)

    def on_sources_found(self, new_sources):
        self.found_sources.extend(new_sources)
        for s in new_sources:
            self.sources_list.addItem(f"[{s.get('quality', 'SD')}] {s.get('source')} ({s.get('provider')})")

    def on_found(self, slist):
        self.progress_container.setVisible(False)
        
        if not self.found_sources:
            self.sources_list.clear()
            self.sources_list.addItem("No sources found.")
        else:
            quality_map = {'4k': 0, '1080p': 1, '720p': 2, 'hd': 2, 'sd': 3, 'cam': 4, 'scr': 4}
            for s in self.found_sources:
                s['q_sort'] = quality_map.get(str(s.get('quality')).lower(), 3)
            self.found_sources.sort(key=lambda x: x['q_sort'])
            
            self.sources_list.clear()
            for s in self.found_sources:
                self.sources_list.addItem(f"[{s.get('quality', 'SD')}] {s.get('source')} ({s.get('provider')})")

    def on_subtitles_found(self, sub_list):
        self.found_subtitles = sub_list
        if not sub_list: 
            self.subtitles_list.addItem("No subtitles found.")
        for s in sub_list:
            self.subtitles_list.addItem(f"[{s.get('service')}] {s.get('lang')}: {s.get('name')}")

    def on_resolve(self, li):
        if self.is_resolving:
            return
            
        idx = self.sources_list.row(li)
        if idx >= len(self.found_sources): return
        source_data = self.found_sources[idx]
        print(f"\n--- RESOLVING ---\nSource: {source_data['source']}\nProvider: {source_data['provider']}")
        
        self.is_resolving = True
        self.edit_stream_url.setText("Resolving stream URL...")
        
        self.resolve_worker = ResolveWorker(source_data, self.get_enabled_packs())
        self.resolve_worker.resolved.connect(self.on_resolved)
        self.resolve_worker.failed.connect(self.on_resolve_failed)
        self.resolve_worker.start()

    def on_resolved(self, final):
        self.is_resolving = False
        self.edit_stream_url.setText(final)
        QApplication.clipboard().setText(final)
        print(f"SUCCESS: {final}")
        QMessageBox.information(self, "Success", "Stream URL resolved and copied to clipboard!")

    def on_resolve_failed(self, err_msg):
        self.is_resolving = False
        self.edit_stream_url.clear()
        QMessageBox.warning(self, "Failed", f"Could not resolve stream: {err_msg}")

    def on_subtitle_selected(self, li):
        if self.is_downloading_sub:
            return
            
        idx = self.subtitles_list.row(li)
        if idx >= len(self.found_subtitles): return
        selected = self.found_subtitles[idx]
        
        self.is_downloading_sub = True
        self.edit_subtitle_url.setText("Downloading subtitle...")
        
        self.sub_download_worker = SubtitleDownloadWorker(
            selected['service_name'],
            selected['action_args'],
            GLOBAL_CONFIG
        )
        self.sub_download_worker.downloaded.connect(self.on_subtitle_downloaded)
        self.sub_download_worker.failed.connect(self.on_subtitle_download_failed)
        self.sub_download_worker.start()

    def on_subtitle_downloaded(self, filepath):
        self.is_downloading_sub = False
        self.edit_subtitle_url.setText(filepath)
        QApplication.clipboard().setText(filepath)
        QMessageBox.information(self, "Success", f"Subtitle downloaded successfully to:\n{filepath}\n\nPath copied to clipboard!")

    def on_subtitle_download_failed(self, err_msg):
        self.is_downloading_sub = False
        self.edit_subtitle_url.clear()
        QMessageBox.warning(self, "Failed", f"Could not download subtitle: {err_msg}")

    def copy_stream_url(self):
        url = self.edit_stream_url.text()
        if url and not self.is_resolving:
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, "Success", "Stream URL copied to clipboard!")

    def copy_subtitle_url(self):
        url = self.edit_subtitle_url.text()
        if url and not self.is_downloading_sub:
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, "Success", "Subtitle URL/Path copied to clipboard!")

if __name__ == "__main__":
    app = QApplication(sys.argv); window = UniversalApp(); window.show(); sys.exit(app.exec())