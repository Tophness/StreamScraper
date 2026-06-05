# StreamScraper

StreamScraper is a standalone cross-platform desktop application that brings together video stream scraping and subtitle searching from popular Kodi addon sources — without requiring Kodi.

Using provider packs adapted from addons such as Free99, The Crew, ScrubsV2, VidSrc, and GratisRed, StreamScraper can search for movies and TV shows, scrape available stream sources, resolve playable URLs, and download subtitles through the A4KSubtitles ecosystem.

## Features

* 🔍 Search movies and TV shows using TMDb
* 🎬 Scrape video streams from multiple Kodi-based provider packs
* 🔗 Resolve hoster links using ResolveURL
* 💬 Search and download subtitles from multiple providers
* 📺 Support for both movies and TV episodes
* ⚡ Multi-threaded scraping engine
* 🛡️ Host whitelist system for filtering sources
* ⚙️ Configurable provider packs and timeout settings
* 🖥️ Cross-platform desktop GUI built with PyQt6
* 🚫 No Kodi installation required

## Screenshots
<img width="1377" height="1039" alt="image" src="https://github.com/user-attachments/assets/b4a6f1db-fcdc-41fe-a251-001a288f13b7" />

## Supported Provider Packs

StreamScraper can load provider packs derived from Kodi addons including:

* Free99
* The Crew
* ScrubsV2
* VidSrc
* GratisRed

Additional provider packs can be added through the `sources/` directory.

## Supported Subtitle Providers

Subtitle functionality is powered by the A4KSubtitles ecosystem and supports:

* Addic7ed
* OpenSubtitles.com
* OpenSubtitles.org
* SubDL
* Subsource
* Podnapisi
* BSPlayer

Provider availability depends on your configuration and API credentials.

## Installation

### Requirements

* Python 3.10 or newer
* Pip
* Git (optional)

### Clone the Repository

```bash
git clone https://github.com/Tophness/StreamScraper.git
cd StreamScraper
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install PyQt6 requests
```

### Launch

```bash
python main.py
```

## Usage

### Searching

1. Enter a movie or TV show title.
2. Click **Search**.
3. Select the desired result.

### TV Shows

1. Select a TV show.
2. Choose a season.
3. Choose an episode.
4. Stream and subtitle searches will begin automatically.

### Stream Sources

1. Select a source from the **Stream Sources** panel.
2. StreamScraper will resolve the source.
3. The final playable URL will be displayed and copied to your clipboard.

### Subtitles

1. Select a subtitle from the **Subtitles** panel.
2. StreamScraper will download the subtitle.
3. The downloaded subtitle path will be displayed and copied to your clipboard.

## How It Works

1. TMDb is used to search for movies and TV shows.
2. Provider packs scrape available stream sources.
3. ResolveURL resolves supported hosts into direct playable URLs.
4. A4KSubtitles-based providers search for matching subtitles.
5. Results are presented in a simple desktop interface without requiring Kodi.

## Credits

This project builds upon the work of many open-source projects and communities, including:

* Free99
* The Crew
* ScrubsV2
* VidSrc
* GratisRed
* ResolveURL
* A4KSubtitles
* TMDb
