import urllib.request
import os
import sys

URL = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
DEST = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = (downloaded / total_size) * 100 if total_size > 0 else 0
    # Print progress every 1% or at completion
    if block_num % 1000 == 0 or percent >= 100:
        sys.stdout.write(f"\rDownloading: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB of {total_size / (1024*1024):.1f} MB)")
        sys.stdout.flush()

def main():
    os.makedirs("models", exist_ok=True)
    print(f"Starting download from: {URL}")
    print(f"Destination: {DEST}")
    
    if os.path.exists(DEST):
        print(f"File already exists at {DEST}. Skipping download.")
        return
        
    try:
        urllib.request.urlretrieve(URL, DEST, download_progress)
        print("\n\n✅ Download completed successfully!")
    except Exception as e:
        print(f"\n❌ Error downloading file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
