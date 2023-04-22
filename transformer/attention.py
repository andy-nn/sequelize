import torch.nn as nn
from .scaled_dp_attn import ScaledDotProductAttention


class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_head, dropout):
        """
        a Multi-Head Attention layer.
        
        Args:
            d_model: The dimensionality of the embedding vector.
            n_head: the number of heads to split the dimension of d_model into.
            dropout: The dropout rate to apply after the attention computation.
        """
        super(MultiHeadAttention, self).__init__()
        # embedding dimension must be divisible by number of heads
        assert d_model % n_head == 0
        
        # key, query, value projections for all heads
        self.c_attn = nn.Linear(d_model, 3 * d_model)
        # output projection
        self.c_proj = nn.Linear(d_model, d_model)

        self.n_head = n_head
        self.d_model = d_model
        
        self.attn = ScaledDotProductAttention(dropout)


    def forward(self, x, *qkv, mask=None):
        """
        Compute multi-head attention over a sequence of embeddings x.

        Args:
            x: tensor of shape (B, S, E), where B is the batch size, S is the sequence length, and E is the embedding dimension.
            qkv: optional tuple of three tensors, each of shape (B, S, E), representing the query, key, and value inputs to the attention layer.
            mask: optional tensor of shape (B, 1, S, S) representing the attention mask to apply.

        Returns:
            y: tensor of shape (B, S, E), the output of the multi-head attention layer.
        """
        # B: batch size, S: sequence length, E: embedding dimension
        B, S, E = x.size()
        # for decoder's second attention layer we use encoder output as key and value
        if qkv:
            q, k, v = qkv
        else:
            # pull out the query, key, value from the concatenated projection
            q, k, v = self.c_attn(x).split(self.d_model, dim=2)
        # split heads and transpose to (B, n_head, S, E // n_head)
        q = q.view(B, S, self.n_head, E // self.n_head).transpose(1, 2)
        k = k.view(B, S, self.n_head, E // self.n_head).transpose(1, 2)
        v = v.view(B, S, self.n_head, E // self.n_head).transpose(1, 2)
        # apply attention
        if mask is not None:
            # for head axis broadcasting
            mask = mask.unsqueeze(1)
        y = self.attn(q, k, v, mask=mask)
        # concatenate heads and transpose to (B, S, E)
        y = y.transpose(1, 2).contiguous().view(B, S, E)
        # apply final linear projection
        y = self.c_proj(y)
        return y