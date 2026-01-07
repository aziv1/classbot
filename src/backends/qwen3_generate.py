import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import gc

checkpoint = "Qwen/Qwen3-0.6B"
local_dir = "src/models/Qwen3-0.6B"
device = "cuda" if torch.cuda.is_available() else "cpu"

_last_model = None
_last_tokenizer = None

def run_llm(prompt):
    global _last_model, _last_tokenizer

    tokenizer, model = load_or_download_model()
    _last_model = model
    _last_tokenizer = tokenizer

    model = model.to(device)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9
        )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)


def unload_llm():
    global _last_model, _last_tokenizer

    try:
        del _last_model
    except:
        pass

    try:
        del _last_tokenizer
    except:
        pass

    _last_model = None
    _last_tokenizer = None

    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()

def load_or_download_model():
    if not os.path.exists(local_dir):
        tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        model = AutoModelForCausalLM.from_pretrained(
            checkpoint,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
        os.makedirs(local_dir, exist_ok=True)
        tokenizer.save_pretrained(local_dir)
        model.save_pretrained(local_dir)
    else:
        tokenizer = AutoTokenizer.from_pretrained(local_dir)
        model = AutoModelForCausalLM.from_pretrained(
            local_dir,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
    return tokenizer, model