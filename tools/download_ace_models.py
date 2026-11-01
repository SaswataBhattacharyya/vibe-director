"""Resumable ACE-Step model setup; downloads files, never loads a GPU model."""
from pathlib import Path
from huggingface_hub import snapshot_download

BASE_REVISION = "82cd0d7b6322bd28cd4e830fe675ddb6180ce36c"
ENCODERS = {
    "m-a-p/MERT-v1-330M": ("5240c2708a5acaee1007f43fb9735c7dcd0b78c9",
        ["config.json", "preprocessor_config.json", "configuration_MERT.py", "modeling_MERT.py", "pytorch_model.bin"]),
    "utter-project/mHuBERT-147": ("7ad3fc0bc5106c58c9c13526abccad527150d135",
        ["config.json", "preprocessor_config.json", "model.safetensors"]),
}

if __name__ == "__main__":
    path = snapshot_download("ACE-Step/ACE-Step-v1-3.5B", revision=BASE_REVISION,
        local_dir=Path.home() / ".cache/ace-step/checkpoints",
        allow_patterns=["ace_step_transformer/*", "music_dcae_f8c8/*", "music_vocoder/*", "umt5-base/*"], max_workers=2)
    print("Base bundle:", path, flush=True)
    for name, (revision, files) in ENCODERS.items():
        path = snapshot_download(name, revision=revision, allow_patterns=files, max_workers=2)
        print(name, path, flush=True)
    print("Downloads complete. No generation or training was started.", flush=True)
