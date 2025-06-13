#!/usr/bin/env python3
"""
Social Media Auto Poster with Flask HTTP Server
Complete version for Google Cloud Run deployment
"""

import requests
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
from io import BytesIO, StringIO
import tempfile
from flask import Flask, jsonify, request, render_template_string
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SocialMediaPoster:
    def __init__(self):
        # Facebook/Instagram API credentials
        self.app_id = "3708785246080823"
        self.app_secret = "ee87767617658dfa4d14ac841bff7efa"
        self.access_token = "EAA0tHtskDzcBOxTOZAxwepQvXGtZAXFixZBP054XoctjXPZAgIwltuwAr2d0rLy6cYR7YR4MFwfRiaSHxR3ZAIyrjsF22AnjnciZCYCl4odHBaa136jgkjjaIEXm0oXN9HEdh3ZCM70oUGkTr7WwkZA07nga8I39rFzEt4w0YiZAwhMDIxutjD8kyC8FzoYgTDbCxxBoNV4W2S8B933zxr8oZD"
        self.facebook_page_id = "105017102705551"
        self.instagram_id = "17841468677012084"
        
        # API endpoints
        self.facebook_api_url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/photos"
        self.instagram_api_url = f"https://graph.facebook.com/v18.0/{self.instagram_id}/media"
        self.instagram_publish_url = f"https://graph.facebook.com/v18.0/{self.instagram_id}/media_publish"
        
        # Default spreadsheet URL
        self.default_spreadsheet_url = "https://docs.google.com/spreadsheets/d/14mo8-qCZNcOeNSsY_GRwHOPyH4LjY5iRneWahK75cZM/edit?pli=1&gid=0#gid=0"

    def load_google_spreadsheet(self, spreadsheet_url):
        """Load data directly from Google Spreadsheet using CSV export URL"""
        try:
            # Convert Google Sheets URL to CSV export URL
            if '/edit' in spreadsheet_url:
                csv_url = spreadsheet_url.replace('/edit#gid=0', '/export?format=csv&gid=0')
                csv_url = csv_url.replace('/edit?pli=1&gid=0#gid=0', '/export?format=csv&gid=0')
                csv_url = csv_url.replace('/edit', '/export?format=csv')
            else:
                csv_url = spreadsheet_url + '/export?format=csv'
            
            logger.info(f"Fetching data from Google Sheets: {csv_url}")
            
            # Download the CSV data
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Load into pandas DataFrame
            df = pd.read_csv(StringIO(response.text))
            
            # Clean column names (remove extra spaces)
            df.columns = df.columns.str.strip()
            
            logger.info(f"Successfully loaded {len(df)} rows from Google Sheets")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading Google Spreadsheet: {e}")
            return None

    def download_image_from_url(self, image_url):
        """Download image from URL and return temporary file path"""
        try:
            logger.info(f"Downloading image from: {image_url}")
            
            # Handle Google Drive URLs
            if 'drive.google.com' in image_url:
                if '/file/d/' in image_url:
                    file_id = image_url.split('/file/d/')[1].split('/')[0]
                    image_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                elif 'id=' in image_url:
                    file_id = image_url.split('id=')[1].split('&')[0]
                    image_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            # Download the image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(image_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            
            # Write image data to temporary file
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            
            temp_file.close()
            
            # Verify file size
            file_size = os.path.getsize(temp_file.name)
            logger.info(f"Image downloaded successfully ({file_size} bytes)")
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None

    def cleanup_temp_file(self, file_path):
        """Clean up temporary file"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Could not delete temp file {file_path}: {e}")

    def parse_datetime(self, date_str, time_str):
        """Parse date and time strings into datetime object"""
        try:
            # Handle various date formats
            date_formats = [
                '%d %B %Y',      # 12 June 2025
                '%d %b %Y',      # 12 Jun 2025
                '%Y-%m-%d',      # 2025-06-12
                '%m/%d/%Y',      # 06/12/2025
                '%d/%m/%Y',      # 12/06/2025
                '%m-%d-%Y',      # 06-12-2025
                '%d-%m-%Y',      # 12-06-2025
                '%B %d, %Y',     # June 12, 2025
                '%b %d, %Y',     # Jun 12, 2025
            ]
            
            # Try to parse date
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(str(date_str).strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                logger.error(f"Could not parse date: {date_str}")
                return None
            
            # Handle various time formats
            time_formats = [
                '%I:%M %p',      # 1:00 PM
                '%I:%M%p',       # 1:00PM
                '%H:%M',         # 13:00
                '%H:%M:%S',      # 13:00:00
                '%I:%M:%S %p'    # 1:00:00 PM
            ]
            
            # Try to parse time
            parsed_time = None
            time_str = str(time_str).strip().upper()
            
            for fmt in time_formats:
                try:
                    time_obj = datetime.strptime(time_str, fmt).time()
                    parsed_time = time_obj
                    break
                except ValueError:
                    continue
            
            if parsed_time is None:
                logger.error(f"Could not parse time: {time_str}")
                return None
            
            # Combine date and time
            full_datetime = datetime.combine(parsed_date.date(), parsed_time)
            return full_datetime
            
        except Exception as e:
            logger.error(f"Error parsing datetime - Date: {date_str}, Time: {time_str}, Error: {e}")
            return None

    def is_time_to_post(self, scheduled_datetime, tolerance_minutes=10):
        """Check if it's time to post based on scheduled datetime"""
        if scheduled_datetime is None:
            return False
        
        current_time = datetime.now()
        time_diff = abs((current_time - scheduled_datetime).total_seconds() / 60)
        
        is_ready = time_diff <= tolerance_minutes
        
        if is_ready:
            logger.info(f"Time to post! Scheduled: {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}")
        
        return is_ready

    def upload_image_to_facebook(self, image_path, caption, hashtags):
        """Upload image to Facebook page"""
        try:
            full_message = f"{caption}\n\n{hashtags}"
            
            files = {'source': open(image_path, 'rb')}
            data = {
                'message': full_message,
                'access_token': self.access_token
            }
            
            response = requests.post(self.facebook_api_url, files=files, data=data, timeout=60)
            files['source'].close()
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Facebook post successful! Post ID: {result.get('id', 'Unknown')}")
                return True, result.get('id')
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                logger.error(f"Facebook post failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Facebook upload error: {e}")
            return False, str(e)

    def upload_image_to_instagram(self, image_url, caption, hashtags):
        """Upload image to Instagram using image_url parameter (2-step process)"""
        try:
            full_caption = f"{caption}\n\n{hashtags}"
            
            data = {
                'image_url': image_url,
                'caption': full_caption,
                'access_token': self.access_token
            }
            
            response = requests.post(self.instagram_api_url, data=data, timeout=60)
            
            if response.status_code != 200:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                logger.error(f"Instagram media creation failed: {error_msg}")
                return False, error_msg
            
            container_id = response.json().get('id')
            logger.info(f"Instagram media container created: {container_id}")
            
            time.sleep(2)
            
            publish_data = {
                'creation_id': container_id,
                'access_token': self.access_token
            }
            
            publish_response = requests.post(self.instagram_publish_url, data=publish_data, timeout=60)
            
            if publish_response.status_code == 200:
                result = publish_response.json()
                logger.info(f"Instagram post successful! Post ID: {result.get('id', 'Unknown')}")
                return True, result.get('id')
            else:
                error_msg = publish_response.json().get('error', {}).get('message', 'Unknown error')
                logger.error(f"Instagram publish failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Instagram upload error: {e}")
            return False, str(e)

    def get_pending_posts(self, spreadsheet_url=None):
        """Get all pending posts from the spreadsheet"""
        if not spreadsheet_url:
            spreadsheet_url = self.default_spreadsheet_url
            
        df = self.load_google_spreadsheet(spreadsheet_url)
        
        if df is None:
            return []
        
        # Map column names
        date_col = 'Date'
        time_col = 'Post Timings'
        caption_col = 'Caption'
        hashtags_col = 'Hashtags'
        imageurl_col = 'Filename.jpg'
        status_col = 'Status'
        
        # Filter pending posts
        pending_posts = df[
            (df[status_col].astype(str).str.lower().isin(['pending', 'scheduled', ''])) |
            (df[status_col].isna()) |
            (df[status_col].astype(str).str.strip() == '')
        ].copy()
        
        posts_data = []
        for index, row in pending_posts.iterrows():
            try:
                date_val = row[date_col]
                time_val = row[time_col]
                
                if pd.isna(date_val) or pd.isna(time_val):
                    continue
                
                scheduled_datetime = self.parse_datetime(date_val, time_val)
                
                posts_data.append({
                    'index': int(index),
                    'date': str(date_val),
                    'time': str(time_val),
                    'scheduled_datetime': scheduled_datetime.strftime('%Y-%m-%d %H:%M') if scheduled_datetime else 'Invalid',
                    'caption': str(row[caption_col])[:100] + '...' if len(str(row[caption_col])) > 100 else str(row[caption_col]),
                    'hashtags': str(row[hashtags_col]),
                    'image_url': str(row[imageurl_col]),
                    'status': str(row[status_col])
                })
            except Exception as e:
                continue
        
        return posts_data

    def process_scheduled_posts(self, spreadsheet_url=None, tolerance_minutes=10):
        """Process posts that are scheduled for the current time"""
        if not spreadsheet_url:
            spreadsheet_url = self.default_spreadsheet_url
            
        df = self.load_google_spreadsheet(spreadsheet_url)
        
        if df is None:
            return []
        
        logger.info(f"Loaded {len(df)} posts from Google Spreadsheet")
        
        # Map column names
        date_col = 'Date'
        time_col = 'Post Timings'
        caption_col = 'Caption'
        hashtags_col = 'Hashtags'
        imageurl_col = 'Filename.jpg'
        status_col = 'Status'
        
        # Filter pending posts
        pending_posts = df[
            (df[status_col].astype(str).str.lower().isin(['pending', 'scheduled', ''])) |
            (df[status_col].isna()) |
            (df[status_col].astype(str).str.strip() == '')
        ].copy()
        
        logger.info(f"Found {len(pending_posts)} pending posts")
        
        # Filter posts ready to publish
        ready_posts = []
        
        for index, row in pending_posts.iterrows():
            try:
                date_val = row[date_col]
                time_val = row[time_col]
                
                if pd.isna(date_val) or pd.isna(time_val):
                    continue
                
                scheduled_datetime = self.parse_datetime(date_val, time_val)
                
                if scheduled_datetime and self.is_time_to_post(scheduled_datetime, tolerance_minutes):
                    ready_posts.append({
                        'index': index,
                        'row': row,
                        'scheduled_datetime': scheduled_datetime
                    })
                    
            except Exception as e:
                logger.error(f"Error checking schedule for row {index + 1}: {e}")
        
        logger.info(f"Found {len(ready_posts)} posts ready to publish")
        
        if len(ready_posts) == 0:
            return []
        
        results = []
        
        for post_info in ready_posts:
            index = post_info['index']
            row = post_info['row']
            temp_image_path = None
            
            try:
                image_url = str(row[imageurl_col]).strip()
                caption = str(row[caption_col]).strip()
                hashtags = str(row[hashtags_col]).strip()
                
                logger.info(f"Processing post for row {index + 1}")
                
                # Download image for Facebook
                temp_image_path = self.download_image_from_url(image_url)
                
                if not temp_image_path:
                    results.append({
                        'index': index,
                        'image_url': image_url,
                        'caption': caption,
                        'facebook_success': False,
                        'instagram_success': False,
                        'error': 'Could not download image'
                    })
                    continue
                
                # Post to Facebook
                fb_success, fb_result = self.upload_image_to_facebook(temp_image_path, caption, hashtags)
                time.sleep(3)
                
                # Post to Instagram
                ig_success, ig_result = self.upload_image_to_instagram(image_url, caption, hashtags)
                
                results.append({
                    'index': index,
                    'image_url': image_url,
                    'caption': caption,
                    'facebook_success': fb_success,
                    'instagram_success': ig_success,
                    'facebook_result': fb_result,
                    'instagram_result': ig_result
                })
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error processing post at row {index + 1}: {e}")
                results.append({
                    'index': index,
                    'image_url': row.get(imageurl_col, 'unknown'),
                    'caption': str(row.get(caption_col, '')),
                    'facebook_success': False,
                    'instagram_success': False,
                    'error': str(e)
                })
            finally:
                if temp_image_path:
                    self.cleanup_temp_file(temp_image_path)
        
        return results

# Initialize Flask app
app = Flask(__name__)
poster = SocialMediaPoster()

# HTML Template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Social Media Auto Poster</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .info { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
        .button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .button:hover { background-color: #0056b3; }
        .button.danger { background-color: #dc3545; }
        .button.danger:hover { background-color: #c82333; }
        .post-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; background: #fafafa; }
        .post-meta { font-size: 0.9em; color: #666; margin-bottom: 10px; }
        .post-content { margin: 10px 0; }
        .image-preview { max-width: 100px; height: auto; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .loading { display: none; text-align: center; padding: 20px; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Social Media Auto Poster Dashboard</h1>
        
        <p class="info status">
            <strong>Current Time:</strong> <span id="current-time"></span><br>
            <strong>Server Status:</strong> <span style="color: green;">🟢 Online</span>
        </p>
        
        <div style="text-align: center; margin: 20px 0;">
            <button class="button" onclick="runScheduler()">▶️ Run Scheduler Now</button>
            <button class="button" onclick="viewPendingPosts()">📋 View Pending Posts</button>
            <button class="button danger" onclick="location.reload()">🔄 Refresh Page</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing...</p>
        </div>
        
        <div id="results"></div>
    </div>

    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleString();
        }
        
        setInterval(updateTime, 1000);
        updateTime();
        
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').innerHTML = '';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        function displayResults(data, title) {
            hideLoading();
            let html = `<h2>${title}</h2>`;
            
            if (data.error) {
                html += `<div class="error status">❌ Error: ${data.error}</div>`;
            } else if (data.message) {
                html += `<div class="info status">ℹ️ ${data.message}</div>`;
            } else if (data.results && data.results.length > 0) {
                html += `<div class="success status">✅ Processed ${data.results.length} posts</div>`;
                html += '<table><tr><th>Row</th><th>Caption</th><th>Facebook</th><th>Instagram</th><th>Status</th></tr>';
                
                data.results.forEach(result => {
                    const fbStatus = result.facebook_success ? '✅' : '❌';
                    const igStatus = result.instagram_success ? '✅' : '❌';
                    const caption = result.caption ? result.caption.substring(0, 50) + '...' : 'No caption';
                    
                    html += `<tr>
                        <td>${result.index + 1}</td>
                        <td>${caption}</td>
                        <td>${fbStatus}</td>
                        <td>${igStatus}</td>
                        <td>${result.error || 'Success'}</td>
                    </tr>`;
                });
                
                html += '</table>';
            } else if (data.posts && data.posts.length > 0) {
                html += `<div class="info status">📋 Found ${data.posts.length} pending posts</div>`;
                
                data.posts.forEach(post => {
                    html += `<div class="post-card">
                        <div class="post-meta">
                            <strong>Row ${post.index + 1}</strong> | 
                            Scheduled: ${post.scheduled_datetime} | 
                            Status: ${post.status}
                        </div>
                        <div class="post-content">
                            <strong>Caption:</strong> ${post.caption}<br>
                            <strong>Hashtags:</strong> ${post.hashtags}
                        </div>
                    </div>`;
                });
            } else {
                html += `<div class="info status">ℹ️ No posts found</div>`;
            }
            
            document.getElementById('results').innerHTML = html;
        }
        
        function runScheduler() {
            showLoading();
            fetch('/api/run-scheduler', { method: 'POST' })
                .then(response => response.json())
                .then(data => displayResults(data, '📅 Scheduler Results'))
                .catch(error => {
                    hideLoading();
                    document.getElementById('results').innerHTML = `<div class="error status">❌ Error: ${error.message}</div>`;
                });
        }
        
        function viewPendingPosts() {
            showLoading();
            fetch('/api/pending-posts')
                .then(response => response.json())
                .then(data => displayResults(data, '📋 Pending Posts'))
                .catch(error => {
                    hideLoading();
                    document.getElementById('results').innerHTML = `<div class="error status">❌ Error: ${error.message}</div>`;
                });
        }
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health_check():
    """Health check endpoint for Google Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'social-media-poster'
    })

@app.route('/api/run-scheduler', methods=['POST'])
def run_scheduler():
    """Run the post scheduler manually"""
    try:
        logger.info("Manual scheduler run triggered")
        
        # Get tolerance from request or use default
        tolerance = request.json.get('tolerance', 10) if request.is_json else 10
        
        # Process scheduled posts
        results = poster.process_scheduled_posts(tolerance_minutes=tolerance)
        
        if not results:
            return jsonify({
                'message': 'No posts scheduled for this time',
                'results': [],
                'total_processed': 0
            })
        
        # Calculate summary stats
        total = len(results)
        fb_success = sum(1 for r in results if r['facebook_success'])
        ig_success = sum(1 for r in results if r['instagram_success'])
        both_success = sum(1 for r in results if r['facebook_success'] and r['instagram_success'])
        
        return jsonify({
            'message': f'Processed {total} posts',
            'results': results,
            'total_processed': total,
            'facebook_success': fb_success,
            'instagram_success': ig_success,
            'both_success': both_success
        })
        
    except Exception as e:
        logger.error(f"Error running scheduler: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/pending-posts')
def get_pending_posts():
    """Get all pending posts"""
    try:
        posts = poster.get_pending_posts()
        
        return jsonify({
            'posts': posts,
            'total_pending': len(posts)
        })
        
    except Exception as e:
        logger.error(f"Error getting pending posts: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/status')
def get_status():
    """Get system status"""
    try:
        return jsonify({
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'service': 'social-media-poster',
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting Social Media Auto Poster server on port {port}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)
