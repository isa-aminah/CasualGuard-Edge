# Full Test Suite Results



**Project:** CAUSALGUARD-EDGE  

**Environment:** Windows, Python 3.11.0  

**Testing Framework:** pytest 9.2.0



## 1. Test Execution



Command executed:



`python -m pytest tests -v`



## 2. Overall Results



| Metric | Result |

|---|---:|

| Total tests passed | 49 |

| Successful subtests | 6 |

| Failed tests | 0 |

| Execution time | 2.90 seconds |



**Final status: ALL TESTS PASSED**



## 3. Test Results by Module



| Test Module | Passed |

|---|---:|

| Alerting | 12 |

| Annotation Pipeline | 4 |

| Braking | 6 |

| Causal Analysis | 4 |

| Counterfactual Analysis | 10 |

| Near-Miss Metrics | 8 |

| Video Library | 5 |

| **Total** | **49** |



## 4. Functional Areas Tested



- Alert generation, severity thresholds and duplicate suppression.

- Annotation label validation and interface rendering.

- Braking displacement calculations.

- Causal-analysis evidence and risk-component handling.

- Counterfactual speed reduction, braking and pedestrian timing scenarios.

- CPA, TTC and PET calculation rules.

- Video library deletion and persisted review-state management.



## 5. Interpretation and Limitations



All 49 tests passed, with 6 successful subtests.



These results demonstrate that the tested software functions behave as expected under the implemented test cases.



They do not establish real-world near-miss detection accuracy, calibrated physical TTC/PET measurements, or the effectiveness of simulated interventions in actual road conditions.



Further validation using independently annotated ground-truth data and real-world calibrated measurements is required.



## 6. Conclusion



The current CAUSALGUARD-EDGE software test suite completed successfully without test failures. The results provide software verification evidence for the implemented modules and their tested functionality.

