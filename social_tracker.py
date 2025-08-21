import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime

# Initialize CSV file
CSV_FILE = 'posts.csv'
try:
    df = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    df = pd.DataFrame(columns=['URL', 'Platform', 'Views', 'Likes', 'Shares', 'Last Updated'])
    df.to_csv(CSV_FILE, index=False)

# Identify platform from URL
def get_platform_from_url(url):
    if 'x.com' in url or 'twitter.com' in url:
        return 'X'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'YouTube'
    elif 'facebook.com' in url:
        return 'Facebook'
    elif 'instagram.com' in url:
        return 'Instagram'
    elif 'tiktok.com' in url:
        return 'TikTok'
    elif 'reddit.com' in url:
        return 'Reddit'
    else:
        return 'Unknown'

# Scrape stats (platform-specific)
def scrape_stats(url, platform):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        views, likes, shares = None, None, None

        if platform == 'X':
            view_elem = soup.find('span', {'data-testid': 'view-count'})
            like_elem = soup.find('span', {'data-testid': 'like'})
            retweet_elem = soup.find('span', {'data-testid': 'retweet'})
            views = int(re.search(r'[\d,]+', view_elem.text).group().replace(',', '')) if view_elem else None
            likes = int(re.search(r'[\d,]+', like_elem.text).group().replace(',', '')) if like_elem else None
            shares = int(re.search(r'[\d,]+', retweet_elem.text).group().replace(',', '')) if retweet_elem else None

        elif platform == 'YouTube':
            view_elem = soup.find('span', class_='view-count')
            like_elem = soup.find('button', {'aria-label': re.compile('like this video', re.I)})
            views = int(re.search(r'[\d,]+', view_elem.text).group().replace(',', '')) if view_elem else None
            likes = int(re.search(r'[\d,]+', like_elem['aria-label']).group().replace(',', '')) if like_elem else None
            shares = None  # Not reliably public

        elif platform == 'Facebook':
            view_elem = soup.find('span', class_='video_view_count')
            like_elem = soup.find('span', text=re.compile('Like', re.I))
            share_elem = soup.find('span', text=re.compile('Share', re.I))
            views = int(re.search(r'[\d,]+', view_elem.text).group().replace(',', '')) if view_elem else None
            likes = int(re.search(r'[\d,]+', like_elem.parent.text).group().replace(',', '')) if like_elem else None
            shares = int(re.search(r'[\d,]+', share_elem.parent.text).group().replace(',', '')) if share_elem else None

        elif platform == 'Reddit':
            score_elem = soup.find('div', {'data-testid': 'post_score'})
            comments_elem = soup.find('span', text=re.compile('Comments', re.I))
            shares = int(re.search(r'[\d,]+', score_elem.text).group().replace(',', '')) if score_elem else None
            views = None  # Not reliably public
            likes = int(re.search(r'[\d,]+', comments_elem.parent.text).group().replace(',', '')) if comments_elem else None

        # Instagram/TikTok require JavaScript rendering; use external tools for now
        return views, likes, shares

    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return None, None, None

# Update all posts
def update_stats():
    df = pd.read_csv(CSV_FILE)
    for index, row in df.iterrows():
        url = row['URL']
        platform = row['Platform']
        views, likes, shares = scrape_stats(url, platform)
        df.loc[index, ['Views', 'Likes', 'Shares', 'Last Updated']] = [views, likes, shares, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    df.to_csv(CSV_FILE, index=False)

# Streamlit UI
st.title("Social Media Post Tracker")
url = st.text_input("Paste Post URL:")
if st.button("Add Post"):
    platform = get_platform_from_url(url)
    if platform != 'Unknown':
        views, likes, shares = scrape_stats(url, platform)
        new_row = pd.DataFrame({
            'URL': [url],
            'Platform': [platform],
            'Views': [views],
            'Likes': [likes],
            'Shares': [shares],
            'Last Updated': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        })
        df = pd.concat([pd.read_csv(CSV_FILE), new_row], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)
        st.success("Post added!")
    else:
        st.error("Unsupported platform.")

# Display list
st.table(pd.read_csv(CSV_FILE))

# Auto-update
if st.button("Start Live Updates"):
    st.write("Updating every 10 minutes...")
    while True:
        update_stats()
        st.experimental_rerun()  # Refresh UI
        time.sleep(600)  # 10 minutes
