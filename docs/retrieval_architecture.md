# Retrieval Architecture: Geospatial Indexing for Landslide Detection

## The Search Problem

TeraAlert processes Sentinel-2 satellite imagery to detect landslides. This is fundamentally a **dense retrieval task**: given a query region (Himalayan zone), efficiently retrieve and rank the most relevant satellite tiles that contain potential landslide features.

### Current Approach: Sequential Scan

The current system fetches satellite data for each monitoring zone sequentially:
1. For each zone (Hamirpur, Kangra, etc.), query STAC API
2. Download 10980x10980 RGB tile
3. Run DeepLabV3+ inference
4. Check if landslide detected

**Problem:** With 16 zones scanning every 5 minutes, this is O(n) per cycle. As we scale to 100+ zones or increase scan frequency, latency grows linearly.

### Proposed Solution: Geospatial Index

Replace sequential scanning with an indexed retrieval system:

```
┌─────────────────────────────────────────────────────────────┐
│                    RETRIEVAL PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Query: Region of Interest (lat, lon, radius)              │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐     │
│  │  H3 Hexagonal Index (Hierarchical Spatial Index)    │     │
│  │  - Level 5 resolution covers ~3.7 km² per hex       │     │
│  │  - Level 6 resolution covers ~0.87 km² per hex      │     │
│  │  - Index all historical landslide coordinates       │     │
│  └────────────────────────────────────────────────────┘     │
│                         ↓                                    │
│  Top-K hex cells ranked by risk score                       │
│                         ↓                                    │
│  Priority queue: Download + process high-risk cells first   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why H3 over R-Trees?

| Factor | R-Tree | H3 (Uber's Hexagonal) |
|--------|--------|----------------------|
| Query flexibility | Bounding boxes only | Points + radius |
| Hierarchical | Yes (nested rectangles) | Yes (nested hexagons) |
| Uniformity | Uneven (depends on data distribution) | Uniform area |
| Use case | Small datasets | Global-scale systems |

H3's uniform hexagons enable consistent query performance regardless of where the region is located.

## Inference Optimization: Mamba/SSM Alternative

### Current: DeepLabV3+ (Transformer-based)

```python
# Current model architecture
model = DeepLabV3Plus(encoder_name='resnet50', in_channels=3, classes=1)
# Inference time: ~180ms on CPU, ~30ms on GPU
```

### Proposed: Mamba State Space Model

Mamba uses Selective State Space Models (SSM) with linear attention, achieving:
- **2x faster inference** than equivalent Transformer
- **O(n)** complexity vs Transformer's O(n²)
- **Constant memory** during generation

```python
# Proposed alternative (hypothetical - requires training)
from mamba_ssm import MambaLMHeadModel

model = MambaLMHeadModel(
    d_model=256,
    d_intermediate=512,
    n_layers=8,
    vocab_size=2  # Binary: landslide / no-landslide
)
# Expected: ~90ms on CPU (2x faster)
```

### Trade-offs

| Aspect | DeepLabV3+ (ResNet) | Mamba/SSM |
|--------|---------------------|-----------|
| Training data needed | Standard dataset | Different architecture |
| Latency | 180ms | ~90ms |
| Accuracy | Baseline | Potential drop (~2-3%) |
| Implementation | Ready | Requires retraining |

### Recommendation

For the FYP, keep DeepLabV3+ (it's working). For MSR-scale optimization:
1. Start with model distillation (smaller encoder)
2. Add H3 indexing for retrieval efficiency
3. Evaluate Mamba as long-term research direction

## Latency Targets

| Scenario | Target | Current |
|----------|--------|---------|
| Single tile inference | <100ms | 180ms |
| Zone scan (16 tiles) | <500ms | ~3s |
| Full coverage (100 zones) | <2s | ~20s |

With H3 indexing + optimized model, we can achieve 10x improvement in retrieval efficiency.