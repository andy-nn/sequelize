import json
import torch
from torchtext.data.utils import get_tokenizer
from tokenizers import ByteLevelBPETokenizer
from transformer import Transformer
from flask import Flask, request, jsonify

app = Flask(__name__)

def load_model():
    checkpoint = torch.load('saved_models/eng2sql.pt', map_location=torch.device('cpu'))
    config = checkpoint['config']
    model = Transformer(config)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    return model

model = load_model()

# load model from pytorch

# load token mappings
src_token2idx = json.load(open('token_mappings/src_token2idx.json', 'r'))
tgt_token2idx = json.load(open('token_mappings/tgt_token2idx.json', 'r'))
tgt_idx2token = dict((idx, token) for token, idx in tgt_token2idx.items())


@app.route('/generate', methods=['POST'])
def generate():
    req = request.get_json(force=True)
    query = req.get('query')
    if not query:
        return jsonify({'error': 'query is required'}), 400
    
    src_tokenizer = get_tokenizer('spacy', language='en_core_web_sm')
    bpe_tokenizer = ByteLevelBPETokenizer.from_file("bpe-tokenizer/vocab.json", "bpe-tokenizer/merges.txt")

    src_tokens = src_tokenizer(query)
    src_tokens = [src_token2idx['<sos>']] + [src_token2idx.get(token, src_token2idx['<unk>']) for token in src_tokens] + [src_token2idx['<eos>']]
    src_tensor = torch.tensor(src_tokens).unsqueeze(0)
    res = model.generate(src_tensor, 100)
    res = res.squeeze(0).tolist()
    res = [tgt_idx2token[idx] for idx in res if idx not in [tgt_token2idx['<sos>'], tgt_token2idx['<eos>'], tgt_token2idx['<pad>']]]
    token_ids = [bpe_tokenizer.token_to_id(token) for token in res]
    res = bpe_tokenizer.decode(token_ids)
    
    return jsonify({'sql': res}), 200
    
    

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4000, debug=True)
