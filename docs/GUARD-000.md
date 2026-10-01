# GUARD-000: When Is the Request Known to Be Valid?

**Status:** guard wire-time analysis implemented  
**Date:** 2026-09-30

Response causality asks whether an output bit depends on information that has
arrived. Guard causality asks a different question: whether the device already
knows the request belongs to a supported family when it drives that bit.

The analyzer locates the last masked request bit on wire time and classifies all
response bits emitted through that symbol as speculative. It distinguishes a
constant speculative prefix from input-dependent speculative output.

For the learned MSB-first corpus, the `0xA?` guard is known after symbol three.
The emitted prefix through that point is constant. For the canonicalized
LSB-first corpus, the equivalent guard is known only at the final symbol while
two early response bits already depend on request data. That model is stream-
causal but has materially riskier guard behavior.

This does not make LSB-first emulation impossible. It means admission policy
must explicitly choose whether a learned family authorizes such speculative
behavior; causality alone is insufficient.
