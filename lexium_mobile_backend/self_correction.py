
"""
Self-Correction Controller
============================
Takes a validation function and LLM service.
No duplicate code - uses your existing GNN + Symbolic + Fusion via validate_fn.

Flow:
    User Question → LLM → Initial Answer (shown to user)
        ↓
    validate_fn(answer) → fused_score
        ↓
    Below threshold? → Re-prompt LLM silently → validate again
        ↓
    Repeat up to max_retries → Return best answer
"""


class SelfCorrectionController:
    """
    Iterative LLM → Validate → Re-prompt loop.
    
    Args:
        validate_fn: Function that takes claim_text and returns validation dict
                     (this is validate_with_neurosymbolic from app.py)
        llm_service: LegalLLMService instance
        threshold: Minimum fused_score to accept (default 0.70)
        max_retries: Max correction iterations (default 3)
    """

    def __init__(self, validate_fn, llm_service, threshold=0.70, max_retries=3):
        self.validate_fn = validate_fn
        self.llm = llm_service
        self.threshold = threshold
        self.max_retries = max_retries
        print(f"✅ Self-Correction Controller ready (threshold={threshold:.0%}, retries={max_retries})")

    def _log_answer(self, tag: str, answer: str):
        print(f"\n=== [{tag}] LLM Output ===")
        print(answer)
        print(f"=== End [{tag}] ===\n")

    def _log_scores(self, tag: str, validation: dict):
        print(f"--- [{tag}] Scores ---")
        print(f"   GNN Score:        {validation.get('gnn_score', 0):.4f}")
        print(f"   Symbolic Conf.:   {validation.get('symbolic_confidence', 0):.4f}")
        print(f"   Fused Score:      {validation.get('fused_score', 0):.4f}")
        print(f"   Rules Satisfied:  {validation.get('num_satisfied', 'N/A')}")
        print(f"   Rules Violated:   {validation.get('num_violations', 'N/A')}")
        print(f"----------------------\n")

    def process(self, question: str, conversation_history: list = None) -> dict:
        """
        Full pipeline.
        
        Returns:
            {
                'answer': str,              # Best answer
                'initial_answer': str,      # First LLM response
                'confidence': dict,         # Best answer's confidence
                'initial_confidence': dict,  # First answer's confidence
                'corrections_made': int,
                'was_corrected': bool
            }
        """
        print(f"\n########## NEW REQUEST (self_correction) ##########")
        print(f"Question: {question}\n")

        # Step 1: Generate initial LLM response
        initial_answer = self.llm.generate(question, conversation_history)
        self._log_answer("INITIAL", initial_answer)

        # Step 2: Validate initial answer
        initial_validation = self.validate_fn(initial_answer)
        initial_score = initial_validation['fused_score']
        initial_confidence = self._build_confidence(initial_validation)
        self._log_scores("INITIAL", initial_validation)

        # Step 3: Check if it passes
        if initial_score >= self.threshold:
            print(f"✅ Initial answer PASSED threshold ({initial_score:.0%} >= {self.threshold:.0%}). No correction needed.")
            print(f"########## REQUEST COMPLETE ##########\n")
            return {
                'answer': initial_answer,
                'initial_answer': initial_answer,
                'confidence': initial_confidence,
                'initial_confidence': initial_confidence,
                'corrections_made': 0,
                'was_corrected': False
            }
        
        print(f"⚠️  Initial answer FAILED threshold ({initial_score:.0%} < {self.threshold:.0%}). Starting correction loop...")

        # Step 4: Correction loop
        best_answer = initial_answer
        best_score = initial_score
        best_validation = initial_validation
        current_validation = initial_validation
        attempts_run = 0

        for attempt in range(1, self.max_retries + 1):
            attempts_run = attempt
            print(f"\n>>> Correction attempt {attempt}/{self.max_retries} <<<")
            try:
                # Re-prompt LLM with feedback (user doesn't see this)
                corrected_answer = self.llm.generate_with_context(
                    question=question,
                    validation_result=current_validation
                )
                self._log_answer(f"ATTEMPT {attempt}", corrected_answer)

                # Validate corrected answer
                corrected_validation = self.validate_fn(corrected_answer)
                corrected_score = corrected_validation['fused_score']
                self._log_scores(f"ATTEMPT {attempt}", corrected_validation)

                # Track best
                if corrected_score > best_score:
                    best_answer = corrected_answer
                    best_score = corrected_score
                    best_validation = corrected_validation
                    print(f"   → New best score: {best_score:.0%}")

                # Pass threshold?
                if corrected_score >= self.threshold:
                    print(f"✅ Attempt {attempt} PASSED threshold ({corrected_score:.0%} >= {self.threshold:.0%}). Stopping.")
                    current_validation = corrected_validation
                    break
                
                print(f"⚠️  Attempt {attempt} still below threshold ({corrected_score:.0%} < {self.threshold:.0%}).")
                current_validation = corrected_validation

            except Exception as e:
                print(f"Correction attempt {attempt} failed: {e}")
                break
        
        print(f"\n########## REQUEST COMPLETE — best score: {best_score:.0%}, attempts used: {attempts_run} ##########\n")

        # Step 5: Return best
        return {
            'answer': best_answer,
            'initial_answer': initial_answer,
            'confidence': self._build_confidence(best_validation),
            'initial_confidence': initial_confidence,
            'corrections_made': attempts_run,
            'was_corrected': best_answer != initial_answer
        }

    def _build_confidence(self, validation: dict) -> dict:
        return {
            'fused_score': validation['fused_score'],
            'gnn_score': validation['gnn_score'],
            'symbolic_confidence': validation['symbolic_confidence'],
            'rules_satisfied': validation['num_satisfied'],
            'rules_violated': validation['num_violations'],
            'is_valid': validation['symbolic_is_valid']
        }

    def _build_feedback(self, validation: dict) -> str:
        """Generate feedback string from violations (used by LLM service)"""
        violations = validation.get('violations', [])
        score = validation.get('fused_score', 0)

        feedback_map = {
            'citation_exists': "Include at least one legal citation.",
            'citations_valid': "Ensure cited statutes are real and accurate.",
            'sufficient_citations': "Include at least 2 legal citations.",
            'legal_language': "Use more formal legal terminology.",
            'proper_format': "Name the specific Act when citing sections.",
            'citation_coherence': "Ensure cited statutes are related.",
            'minimum_length': "Provide more detail (at least 5 words per claim).",
            'not_gibberish': "Ensure the response is coherent.",
            'logical_consistency': "Remove contradictory statements.",
            'complete_claim': "Include citations and sufficient detail.",
        }

        parts = [f"Score: {score:.0%} (needs {self.threshold:.0%}). Fix:"]
        for v in violations:
            clean = v.split(' (error:')[0]
            parts.append(f"- {feedback_map.get(clean, clean.replace('_', ' '))}")

        return "\n".join(parts)