from flask import Flask, request, jsonify
import yt_dlp
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for n8n requests

class TranscriptExtractor:
    def __init__(self):
        self.ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB'],  # Prefer English
        }
    
    def extract_transcript(self, video_id):
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extract info without downloading
                info = ydl.extract_info(url, download=False)
                
                # Get subtitles
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                # Try to get English subtitles first
                transcript_text = ""
                
                # Priority: manual subtitles > automatic captions
                for lang in ['en', 'en-US', 'en-GB']:
                    if lang in subtitles:
                        # For manual subtitles, we need to download the content
                        subtitle_url = subtitles[lang][0]['url']
                        transcript_text = self._download_subtitle_content(subtitle_url)
                        break
                    elif lang in automatic_captions:
                        subtitle_url = automatic_captions[lang][0]['url']
                        transcript_text = self._download_subtitle_content(subtitle_url)
                        break
                
                return {
                    'success': True,
                    'video_id': video_id,
                    'transcript': transcript_text,
                    'has_transcript': bool(transcript_text),
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '')
                }
                
        except Exception as e:
            return {
                'success': False,
                'video_id': video_id,
                'error': str(e),
                'transcript': '',
                'has_transcript': False
            }
    
    def _download_subtitle_content(self, subtitle_url):
        """Download and parse subtitle content"""
        try:
            import requests
            import xml.etree.ElementTree as ET
            import html
            import re
            
            response = requests.get(subtitle_url)
            response.raise_for_status()
            
            # Parse XML subtitle content
            root = ET.fromstring(response.content)
            transcript_parts = []
            
            for text_elem in root.findall('.//text'):
                text_content = text_elem.text
                if text_content:
                    # Clean up the text
                    text_content = html.unescape(text_content)
                    text_content = re.sub(r'<[^>]+>', '', text_content)  # Remove HTML tags
                    transcript_parts.append(text_content.strip())
            
            return ' '.join(transcript_parts)
            
        except Exception as e:
            print(f"Error downloading subtitle content: {e}")
            return ""

# Initialize extractor
extractor = TranscriptExtractor()

@app.route('/extract-transcript', methods=['POST'])
def extract_transcript():
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        
        if not video_id:
            return jsonify({'error': 'video_id is required'}), 400
        
        result = extractor.extract_transcript(video_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract-multiple', methods=['POST'])
def extract_multiple():
    try:
        data = request.get_json()
        video_ids = data.get('video_ids', [])
        
        if not video_ids:
            return jsonify({'error': 'video_ids array is required'}), 400
        
        results = []
        for video_id in video_ids:
            result = extractor.extract_transcript(video_id)
            results.append(result)
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'youtube-transcript-extractor'})

if __name__ == '__main__':
    print("Starting YouTube Transcript Extraction Service...")
    print("Install dependencies: pip install flask yt-dlp flask-cors requests")
    app.run(host='0.0.0.0', port=5000, debug=True)