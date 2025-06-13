#!/usr/bin/env python3
"""
Social Media Auto Poster - Complete Working Version
Includes Instagram fix and all functionality
"""

import requests
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
from io import BytesIO, StringIO
import tempfile

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
            
            print(f"📡 Fetching data from Google Sheets...")
            print(f"   URL: {csv_url}")
            
            # Download the CSV data
            response = requests.get(csv_url)
            response.raise_for_status()
            
            # Load into pandas DataFrame
            df = pd.read_csv(StringIO(response.text))
            
            # Clean column names (remove extra spaces)
            df.columns = df.columns.str.strip()
            
            print(f"📊 Successfully loaded {len(df)} rows from Google Sheets")
            print(f"📋 Columns found: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error loading Google Spreadsheet: {e}")
            print("💡 Make sure your Google Sheet is shared publicly (Anyone with the link can view)")
            return None

    def download_image_from_url(self, image_url):
        """Download image from URL and return temporary file path"""
        try:
            print(f"📥 Downloading image from: {image_url}")
            
            # Handle Google Drive URLs
            if 'drive.google.com' in image_url:
                # Extract file ID from Google Drive URL
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
            
            response = requests.get(image_url, headers=headers, stream=True)
            response.raise_for_status()
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            
            # Write image data to temporary file
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            
            temp_file.close()
            
            # Verify file size
            file_size = os.path.getsize(temp_file.name)
            print(f"✅ Image downloaded successfully ({file_size} bytes)")
            
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Error downloading image from {image_url}: {e}")
            return None

    def cleanup_temp_file(self, file_path):
        """Clean up temporary file"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"⚠️  Warning: Could not delete temp file {file_path}: {e}")

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
                print(f"❌ Could not parse date: {date_str}")
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
            time_str = str(time_str).strip().upper()  # Convert to uppercase for PM/AM
            
            for fmt in time_formats:
                try:
                    time_obj = datetime.strptime(time_str, fmt).time()
                    parsed_time = time_obj
                    break
                except ValueError:
                    continue
            
            if parsed_time is None:
                print(f"❌ Could not parse time: {time_str}")
                return None
            
            # Combine date and time
            full_datetime = datetime.combine(parsed_date.date(), parsed_time)
            return full_datetime
            
        except Exception as e:
            print(f"❌ Error parsing datetime - Date: {date_str}, Time: {time_str}, Error: {e}")
            return None

    def is_time_to_post(self, scheduled_datetime, tolerance_minutes=10):
        """Check if it's time to post based on scheduled datetime"""
        if scheduled_datetime is None:
            return False
        
        current_time = datetime.now()
        time_diff = abs((current_time - scheduled_datetime).total_seconds() / 60)  # difference in minutes
        
        # Check if current time is within tolerance of scheduled time
        is_ready = time_diff <= tolerance_minutes
        
        if is_ready:
            print(f"✅ Time to post! Scheduled: {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}, Current: {current_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"⏰ Not time yet. Scheduled: {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}, Current: {current_time.strftime('%Y-%m-%d %H:%M')}, Diff: {time_diff:.1f} min")
        
        return is_ready

    def upload_image_to_facebook(self, image_path, caption, hashtags):
        """Upload image to Facebook page"""
        try:
            # Combine caption and hashtags
            full_message = f"{caption}\n\n{hashtags}"
            
            # Prepare the request
            files = {'source': open(image_path, 'rb')}
            data = {
                'message': full_message,
                'access_token': self.access_token
            }
            
            response = requests.post(self.facebook_api_url, files=files, data=data)
            files['source'].close()
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Facebook post successful! Post ID: {result.get('id', 'Unknown')}")
                return True, result.get('id')
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                print(f"❌ Facebook post failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            print(f"❌ Facebook upload error: {e}")
            return False, str(e)

    def upload_image_to_instagram(self, image_url, caption, hashtags):
        """Upload image to Instagram using image_url parameter (2-step process)"""
        try:
            # Step 1: Create media container using image_url
            full_caption = f"{caption}\n\n{hashtags}"
            
            # Instagram requires image_url parameter, not file upload
            data = {
                'image_url': image_url,  # Use the original URL directly
                'caption': full_caption,
                'access_token': self.access_token
            }
            
            response = requests.post(self.instagram_api_url, data=data)
            
            if response.status_code != 200:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                print(f"❌ Instagram media creation failed: {error_msg}")
                return False, error_msg
            
            container_id = response.json().get('id')
            print(f"📷 Instagram media container created: {container_id}")
            
            # Step 2: Publish the media
            time.sleep(2)  # Wait a moment before publishing
            
            publish_data = {
                'creation_id': container_id,
                'access_token': self.access_token
            }
            
            publish_response = requests.post(self.instagram_publish_url, data=publish_data)
            
            if publish_response.status_code == 200:
                result = publish_response.json()
                print(f"✅ Instagram post successful! Post ID: {result.get('id', 'Unknown')}")
                return True, result.get('id')
            else:
                error_msg = publish_response.json().get('error', {}).get('message', 'Unknown error')
                print(f"❌ Instagram publish failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            print(f"❌ Instagram upload error: {e}")
            return False, str(e)

    def update_google_sheet_status(self, spreadsheet_url, row_index, new_status):
        """Note: This would require Google Sheets API credentials to write back to the sheet."""
        print(f"📝 Status update needed for row {row_index + 1}: {new_status}")
        print("💡 To automatically update status in Google Sheets, you'll need to set up Google Sheets API")

    def process_scheduled_posts(self, spreadsheet_url, tolerance_minutes=10):
        """Process posts that are scheduled for the current time from Google Spreadsheet"""
        df = self.load_google_spreadsheet(spreadsheet_url)
        
        if df is None:
            print("❌ Could not load Google Spreadsheet data")
            return
        
        print(f"📊 Loaded {len(df)} posts from Google Spreadsheet")
        current_time = datetime.now()
        print(f"🕐 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Map your specific column names
        date_col = 'Date'
        time_col = 'Post Timings'
        caption_col = 'Caption'
        hashtags_col = 'Hashtags'
        imageurl_col = 'Filename.jpg'
        status_col = 'Status'
        
        print(f"📋 Using columns:")
        print(f"   Date: {date_col}")
        print(f"   Time: {time_col}")
        print(f"   Caption: {caption_col}")
        print(f"   Hashtags: {hashtags_col}")
        print(f"   Image URL: {imageurl_col}")
        print(f"   Status: {status_col}")
        
        # Filter posts that haven't been posted yet
        pending_posts = df[
            (df[status_col].astype(str).str.lower().isin(['pending', 'scheduled', ''])) |
            (df[status_col].isna()) |
            (df[status_col].astype(str).str.strip() == '')
        ].copy()
        
        print(f"📝 Found {len(pending_posts)} pending posts")
        
        # Filter posts that are scheduled for now (within tolerance)
        ready_posts = []
        
        for index, row in pending_posts.iterrows():
            try:
                date_val = row[date_col]
                time_val = row[time_col]
                
                # Skip if date or time is empty/NaN
                if pd.isna(date_val) or pd.isna(time_val) or str(date_val).strip() == '' or str(time_val).strip() == '':
                    print(f"⚠️  Skipping row {index + 1}: Missing date or time")
                    continue
                
                scheduled_datetime = self.parse_datetime(date_val, time_val)
                
                if scheduled_datetime and self.is_time_to_post(scheduled_datetime, tolerance_minutes):
                    ready_posts.append({
                        'index': index,
                        'row': row,
                        'scheduled_datetime': scheduled_datetime
                    })
                    
            except Exception as e:
                print(f"❌ Error checking schedule for row {index + 1}: {e}")
        
        print(f"🎯 Found {len(ready_posts)} posts ready to publish now")
        
        if len(ready_posts) == 0:
            print("😴 No posts scheduled for this time. Exiting.")
            return []
        
        results = []
        
        for post_info in ready_posts:
            index = post_info['index']
            row = post_info['row']
            scheduled_datetime = post_info['scheduled_datetime']
            temp_image_path = None
            
            try:
                image_url = str(row[imageurl_col]).strip()
                caption = str(row[caption_col]).strip()
                hashtags = str(row[hashtags_col]).strip()
                
                print(f"\n📌 Processing post for: {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}")
                print(f"   Image URL: {image_url}")
                print(f"   Caption: {caption[:50]}...")
                
                # For Facebook: Download image and upload file
                temp_image_path = self.download_image_from_url(image_url)
                
                if not temp_image_path:
                    print(f"❌ Could not download image from: {image_url}")
                    results.append({
                        'index': index,
                        'image_url': image_url,
                        'facebook_success': False,
                        'instagram_success': False,
                        'error': 'Could not download image'
                    })
                    continue
                
                # Post to Facebook (uses downloaded file)
                print("📘 Posting to Facebook...")
                fb_success, fb_result = self.upload_image_to_facebook(temp_image_path, caption, hashtags)
                
                # Wait between posts to avoid rate limits
                time.sleep(3)
                
                # Post to Instagram (uses original URL directly)
                print("📷 Posting to Instagram...")
                ig_success, ig_result = self.upload_image_to_instagram(image_url, caption, hashtags)
                
                # Record results
                results.append({
                    'index': index,
                    'image_url': image_url,
                    'facebook_success': fb_success,
                    'instagram_success': ig_success,
                    'facebook_result': fb_result,
                    'instagram_result': ig_result
                })
                
                # Update status
                if fb_success and ig_success:
                    new_status = 'Posted'
                elif fb_success or ig_success:
                    new_status = 'Partially Posted'
                else:
                    new_status = 'Failed'
                
                self.update_google_sheet_status(spreadsheet_url, index, new_status)
                
                # Wait between posts
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Error processing post at row {index + 1}: {e}")
                results.append({
                    'index': index,
                    'image_url': row.get(imageurl_col, 'unknown'),
                    'facebook_success': False,
                    'instagram_success': False,
                    'error': str(e)
                })
            finally:
                # Clean up temporary image file
                if temp_image_path:
                    self.cleanup_temp_file(temp_image_path)
        
        # Print summary
        self.print_summary(results)
        
        return results

    def print_summary(self, results):
        """Print a summary of posting results"""
        print("\n" + "="*50)
        print("📊 POSTING SUMMARY")
        print("="*50)
        
        total = len(results)
        fb_success = sum(1 for r in results if r['facebook_success'])
        ig_success = sum(1 for r in results if r['instagram_success'])
        both_success = sum(1 for r in results if r['facebook_success'] and r['instagram_success'])
        
        print(f"Total posts processed: {total}")
        print(f"Facebook successful: {fb_success}/{total}")
        print(f"Instagram successful: {ig_success}/{total}")
        print(f"Both platforms successful: {both_success}/{total}")
        
        # Show failed posts
        failed_posts = [r for r in results if not (r['facebook_success'] and r['instagram_success'])]
        if failed_posts:
            print(f"\n❌ Failed/Partial posts ({len(failed_posts)}):")
            for post in failed_posts:
                print(f"   • Row {post['index'] + 1}: {post.get('image_url', 'Unknown URL')}")
                if 'error' in post:
                    print(f"     Error: {post['error']}")

def main():
    """Main function to run the social media poster"""
    poster = SocialMediaPoster()
    
    # Configuration
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/14mo8-qCZNcOeNSsY_GRwHOPyH4LjY5iRneWahK75cZM/edit?pli=1&gid=0#gid=0"
    tolerance_minutes = 10  # How many minutes early/late to allow posting
    
    print("🚀 Starting Social Media Auto Poster")
    print("="*60)
    
    # Process posts (only those scheduled for current time)
    results = poster.process_scheduled_posts(spreadsheet_url, tolerance_minutes)
    
    print("\n✅ Script completed!")
    print(f"\n💡 TIP: Run this script every {tolerance_minutes} minutes to automatically post scheduled content")

if __name__ == "__main__":
    main()
