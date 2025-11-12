# AI Enhancement Strategy: Moving from Rules to Intelligence

## Current State: Rule-Based System

The system currently relies heavily on:
- **Keyword matching** for domain classification
- **Pattern matching** for implied vulnerability generation
- **Fixed thresholds** for validation
- **Simple text similarity** for deduplication
- **Hardcoded lists** for categorization

## Target State: AI-Driven Intelligence

Replace rule-based logic with semantic understanding and context-aware decisions.

---

## Implementation Plan

### Phase 1: AI Validation & Quality Assessment (HIGH PRIORITY)

**Replace**: Simple word overlap validation  
**With**: AI semantic validation

**Benefits**:
- Prevents hallucinations more effectively
- Understands context, not just keywords
- Provides evidence for validation decisions

**Implementation**: `ai_validate_extraction()` in `services/ai_enhancer.py`

---

### Phase 2: AI Domain Classification (HIGH PRIORITY)

**Replace**: Keyword-based domain mapping (`add_domain_defaults`)  
**With**: AI semantic classification

**Benefits**:
- Understands context, not just keywords
- Handles edge cases better
- Provides reasoning for classification

**Implementation**: `ai_classify_domain()` in `services/ai_enhancer.py`

**Example**:
- **Before**: "bollard" → "Perimeter" (keyword match)
- **After**: AI understands "vehicle barrier system" → "Perimeter Security" (semantic understanding)

---

### Phase 3: AI Implied Vulnerability Generation (MEDIUM PRIORITY)

**Replace**: Keyword-based implied vulnerability generation  
**With**: AI contextual generation

**Benefits**:
- More specific and meaningful implied vulnerabilities
- Context-aware generation
- Better than generic "(Implied design weakness)"

**Implementation**: `ai_generate_implied_vulnerability()` in `services/ai_enhancer.py`

**Example**:
- **Before**: OFC "Install bollards" → "(Implied: Missing or inadequate perimeter security)"
- **After**: OFC "Install bollards at vehicle entry points" → "(Implied: Inadequate vehicle access control at entry points)"

---

### Phase 4: AI Quality Assessment (MEDIUM PRIORITY)

**Replace**: Fixed confidence thresholds  
**With**: AI quality scoring

**Benefits**:
- Dynamic confidence scoring based on content quality
- Identifies issues and provides recommendations
- More nuanced than binary pass/fail

**Implementation**: `ai_assess_quality()` in `services/ai_enhancer.py`

---

### Phase 5: AI Semantic Deduplication (LOW PRIORITY)

**Replace**: Simple text similarity (SequenceMatcher)  
**With**: AI semantic similarity

**Benefits**:
- Understands when records are semantically equivalent
- Better merge decisions
- Suggests merged text

**Implementation**: `ai_should_merge()` in `services/ai_enhancer.py`

**Example**:
- **Before**: "Lack of visitor management" vs "Missing visitor policy" → Not merged (low text similarity)
- **After**: AI recognizes semantic equivalence → Merged

---

## Integration Points

### 1. Post-Processing Enhancement

**File**: `services/postprocess.py`

**Changes**:
- Replace `add_domain_defaults()` with `ai_classify_domain()`
- Replace implied vulnerability generation with `ai_generate_implied_vulnerability()`
- Add `ai_validate_extraction()` before record acceptance
- Use `ai_assess_quality()` for confidence scoring

**Example**:
```python
# Before
if not rec.get("category"):
    # Keyword matching
    for domain, keywords in domain_keywords.items():
        if keyword in combined_text:
            rec["category"] = domain

# After
if not rec.get("category") or rec.get("category_confidence", 1.0) < 0.7:
    domain_result = ai_classify_domain(vuln, ofc_text, source_context)
    rec["category"] = domain_result["category"]
    rec["category_confidence"] = domain_result["confidence"]
```

---

### 2. Validation Layer

**File**: `services/postprocess.py` (in `postprocess_results`)

**Changes**:
- Replace word overlap validation with `ai_validate_extraction()`
- Use AI validation results to filter records

**Example**:
```python
# Before
overlap = len(vuln_words & context_words) / max(len(vuln_words), 1)
if overlap < min_overlap:
    skip_record()

# After
validation = ai_validate_extraction(vuln, source_context)
if not validation["is_valid"]:
    skip_record()
```

---

### 3. Deduplication Enhancement

**File**: `services/postprocess.py` (in `merge_similar_duplicates`)

**Changes**:
- Use `ai_should_merge()` for merge decisions
- Apply AI-suggested merged text

**Example**:
```python
# Before
similarity = SequenceMatcher(None, vuln1, vuln2).ratio()
if similarity >= threshold:
    merge()

# After
merge_decision = ai_should_merge(rec1, rec2)
if merge_decision["should_merge"]:
    merged_text = merge_decision["merged_suggestion"] or vuln1
    merge()
```

---

## Performance Considerations

### Caching Strategy
- Cache AI results for identical inputs
- Use hash of (vuln_text, ofc_text, context) as cache key
- Cache TTL: 24 hours

### Batch Processing
- Process multiple records in single AI call when possible
- Use batch prompts for efficiency

### Fallback Behavior
- If AI fails, fall back to rule-based logic
- Log AI failures for monitoring
- Don't block processing if AI is unavailable

### Rate Limiting
- Limit concurrent AI calls
- Queue AI requests if needed
- Use async processing for non-blocking operations

---

## Configuration

### Environment Variables
```bash
# Enable AI enhancement
ENABLE_AI_ENHANCEMENT=true

# AI model for enhancement (default: same as extraction model)
AI_ENHANCEMENT_MODEL=vofc-engine:v3

# AI enhancement confidence threshold
AI_MIN_CONFIDENCE=0.6

# Cache AI results
AI_CACHE_ENABLED=true
AI_CACHE_TTL=86400  # 24 hours
```

### Feature Flags
- `AI_VALIDATION_ENABLED`: Enable AI validation
- `AI_CLASSIFICATION_ENABLED`: Enable AI domain classification
- `AI_QUALITY_ASSESSMENT_ENABLED`: Enable AI quality scoring
- `AI_DEDUPLICATION_ENABLED`: Enable AI semantic deduplication

---

## Expected Improvements

| Metric | Before (Rules) | After (AI) | Improvement |
|--------|----------------|------------|-------------|
| Domain Classification Accuracy | 70% | 90%+ | +20% |
| False Positive Rate | 15% | 5% | -10% |
| Implied Vulnerability Quality | Low (generic) | High (specific) | Significant |
| Validation Accuracy | 80% | 95%+ | +15% |
| Deduplication Precision | 75% | 90%+ | +15% |

---

## Migration Path

1. **Week 1**: Implement `ai_enhancer.py` with all functions
2. **Week 2**: Integrate AI validation (Phase 1)
3. **Week 3**: Integrate AI classification (Phase 2)
4. **Week 4**: Integrate AI implied vulnerability generation (Phase 3)
5. **Week 5**: Integrate AI quality assessment (Phase 4)
6. **Week 6**: Integrate AI deduplication (Phase 5)
7. **Week 7**: Performance optimization and caching
8. **Week 8**: Full rollout with fallback to rules

---

## Monitoring

### Metrics to Track
- AI call success rate
- AI response time
- AI vs rule-based accuracy comparison
- Cache hit rate
- Fallback usage rate

### Logging
- Log all AI decisions with reasoning
- Track AI confidence scores
- Monitor AI failures and fallbacks

---

## Future Enhancements

1. **Self-Learning**: Use AI to improve its own prompts based on feedback
2. **Multi-Model Ensemble**: Use multiple models and vote on decisions
3. **Fine-Tuning**: Fine-tune model on validated extractions
4. **Contextual Memory**: Remember document context across chunks
5. **Adaptive Thresholds**: Let AI determine optimal thresholds per document type

