import subprocess
import sys

def install_spacy_model():
    """Install required spaCy model"""
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✅ spaCy model installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install spaCy model")

if __name__ == "__main__":
    install_spacy_model()