from flask import Flask, render_template, request, jsonify
import os
from pathlib import Path
from kokoro import KPipeline, KModel
import torch
import soundfile as sf
from loguru import logger
import time
import requests
import tempfile
from config import load_config, save_config

app = Flask(__name__)

# Load configuration
config = load_config()


# TTS Functions
def initialize_model(use_gpu=False):
    """Initialize the Kokoro model with proper device selection."""
    model = KModel()
    if use_gpu and torch.cuda.is_available():
        model = model.to('cuda')
        logger.info("Using GPU for synthesis")
    else:
        model = model.to('cpu')
        logger.info("Using CPU for synthesis")
    return model.eval()

def split_text(text, max_length=500):
    """Split text into chunks, trying to break at sentences."""
    chunks = []
    current_chunk = []
    current_length = 0
    
    sentences = text.replace('\n', ' ').split('. ')
    
    for sentence in sentences:
        sentence = sentence + '. ' if sentence != sentences[-1] else sentence
        
        if current_length + len(sentence) > max_length:
            if current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        current_chunk.append(sentence)
        current_length += len(sentence)
    
    if current_chunk:
        chunks.append(''.join(current_chunk))
    
    return chunks

def text_to_speech(pipeline, model, text_chunk, output_dir, chunk_num, voice):
    """Convert text chunk to speech using Kokoro."""
    try:
        temp_path = output_dir / f"chunk_{chunk_num:04d}.wav"
        pack = pipeline.load_voice(voice)
        
        for _, ps, _ in pipeline(text_chunk, voice):
            if ps:
                ref_s = pack[len(ps)-1]
                audio = model(ps, ref_s, speed=1.0)
                if audio is not None:
                    sf.write(temp_path, audio.cpu().numpy(), 24000)
                    logger.info(f"Saved chunk {chunk_num}")
                    return temp_path
            
        return None
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_num}: {e}")
        return None

def concatenate_audio_files(audio_files, output_file):
    """Concatenate WAV files."""
    import numpy as np
    
    data, sample_rate = sf.read(audio_files[0])
    total_data = [data]
    
    for file_path in audio_files[1:]:
        data, _ = sf.read(file_path)
        total_data.append(data)
    
    combined = np.concatenate(total_data)
    sf.write(output_file, combined, sample_rate)

# Audiobookshelf Upload Functions
class AudiobookshelfUploader:
    def __init__(self, server_url, api_token):
        self.server_url = server_url.rstrip('/')
        self.api_token = api_token
        self.headers = {'Authorization': f'Bearer {api_token}'}

    def get_collection_id(self, collection_name):
        response = requests.get(
            f'{self.server_url}/api/collections',
            headers=self.headers
        )
        response.raise_for_status()
        
        collections = response.json().get('collections', [])
        for collection in collections:
            if collection['name'].lower() == collection_name.lower():
                return collection['id']
        return None

    def get_library_and_folder_ids(self):
        response = requests.get(
            f'{self.server_url}/api/libraries',
            headers=self.headers
        )
        response.raise_for_status()
        
        libraries = response.json().get('libraries', [])
        for library in libraries:
            if library['mediaType'] == 'book':
                if library.get('folders') and len(library['folders']) > 0:
                    return library['id'], library['folders'][0]['id']
        
        raise Exception("No suitable audiobook library found")

    def upload_and_add_to_collection(self, audio_file_path, title, collection_name="textlistens"):
        try:
            logger.info(f"Looking for collection: {collection_name}")
            response = requests.get(
                f'{self.server_url}/api/collections',
                headers=self.headers
            )
            response.raise_for_status()
            
            collections = response.json().get('collections', [])
            logger.info(f"Available collections: {[c['name'] for c in collections]}")
            
            collection_id = self.get_collection_id(collection_name)
            if not collection_id:
                raise Exception(f"Collection '{collection_name}' not found. Available collections: {[c['name'] for c in collections]}")

            library_id, folder_id = self.get_library_and_folder_ids()
            
            files = {
                'audioFile': (os.path.basename(audio_file_path), open(audio_file_path, 'rb')),
            }
            
            data = {
                'title': title,
                'library': library_id,
                'folder': folder_id
            }
            
            response = requests.post(
                f'{self.server_url}/api/upload',
                headers=self.headers,
                data=data,
                files=files
            )
            response.raise_for_status()
            
            if response.text.strip() == "OK":
                logger.info("Initial upload successful, waiting for processing...")
                time.sleep(1)
                
                logger.info(f"Fetching recently added items from library {library_id}")
                response = requests.get(
                    f'{self.server_url}/api/libraries/{library_id}/items',
                    headers=self.headers,
                    params={'sort': 'addedAt', 'desc': 1, 'limit': 1}
                )
                response.raise_for_status()
                
                items = response.json().get('results', [])
                logger.info(f"Found items: {items}")
                
                if items:
                    library_item_id = items[0]['id']
                    logger.info(f"Got library item ID: {library_item_id}")
                    try:
                        self.add_to_collection(library_item_id, collection_id)
                        logger.info("Successfully added to collection")
                    except Exception as e:
                        logger.warning(f"Failed to add to collection, but file was uploaded successfully: {str(e)}")
                    return library_item_id
                    
            raise Exception("Upload failed")
            
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            raise

    def add_to_collection(self, library_item_id, collection_id):
        url = f'{self.server_url}/api/collections/{collection_id}/book'
        payload = {'id': library_item_id}
        
        logger.info(f"Adding to collection - URL: {url}")
        logger.info(f"Payload: {payload}")
        logger.info(f"Headers: {self.headers}")
        
        response = requests.post(
            url,
            headers=self.headers,
            json=payload
        )
        
        if not response.ok:
            logger.error(f"Failed to add to collection. Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
        response.raise_for_status()

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    return jsonify(config)

@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration."""
    try:
        # Debug incoming request
        logger.info(f"Received config update request with content type: {request.content_type}")
        logger.info(f"Request data: {request.get_data()}")
        
        if not request.is_json:
            logger.error("Request content-type is not application/json")
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        new_config = request.get_json()
        logger.info(f"Parsed JSON config: {new_config}")
        
        if not new_config:
            logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400

        # Validate configuration
        required_fields = ['AUDIOBOOKSHELF_URL', 'AUDIOBOOKSHELF_TOKEN']
        if not all(field in new_config for field in required_fields):
            logger.error("Missing required configuration fields")
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Update config
        config.update(new_config)
        save_config(config)
        logger.info("Configuration saved to file")
        
        # Test connection
        uploader = AudiobookshelfUploader(
            config['AUDIOBOOKSHELF_URL'],
            config['AUDIOBOOKSHELF_TOKEN']
        )
        try:
            uploader.get_library_and_folder_ids()
            logger.info("Configuration test successful")
            return jsonify({'message': 'Configuration updated and connection tested successfully'})
        except Exception as e:
            logger.error(f"Configuration test failed: {str(e)}")
            return jsonify({'error': f'Configuration saved but connection test failed: {str(e)}'}), 400
            
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_text():
    try:
        AUDIOBOOKSHELF_URL = config['AUDIOBOOKSHELF_URL']
        AUDIOBOOKSHELF_TOKEN = config['AUDIOBOOKSHELF_TOKEN']
        text = request.form.get('text')
        title = request.form.get('title')
        voice = request.form.get('voice', 'af_sarah')  # Default voice
        use_gpu = torch.cuda.is_available()
        
        if not text or not title:
            return jsonify({'error': 'Text and title are required'}), 400

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            output_file = temp_dir_path / f"{title}.wav"
            
            # Initialize TTS
            model = initialize_model(use_gpu)
            pipeline = KPipeline(lang_code=voice[0])
            
            # Process text
            chunks = split_text(text)
            audio_files = []
            
            for i, chunk in enumerate(chunks, 1):
                temp_path = text_to_speech(pipeline, model, chunk, temp_dir_path, i, voice)
                if temp_path:
                    audio_files.append(temp_path)
            
            if audio_files:
                # Combine audio files
                concatenate_audio_files([str(f) for f in audio_files], output_file)
                
                # Upload to Audiobookshelf
                uploader = AudiobookshelfUploader(AUDIOBOOKSHELF_URL, AUDIOBOOKSHELF_TOKEN)
                library_item_id = uploader.upload_and_add_to_collection(str(output_file), title)
                
                return jsonify({
                    'success': True,
                    'message': 'Processing complete',
                    'library_item_id': library_item_id,
                    'server_url': config['AUDIOBOOKSHELF_URL']  # Add this line
                })
            
            return jsonify({'error': 'Failed to generate audio'}), 500
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 10108))
    app.run(host='0.0.0.0', port=port, debug=False)