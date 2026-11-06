# Product brief
**Audience:** analytics engineers, BI teams, data scientists and small organizations.
**Primary workflow:** upload a CSV, review quality score, inspect column-level issues, and use profile findings to improve source data.
**Metric definitions:** completeness = non-null cells / all cells; uniqueness = 1 - duplicate rows / row count; score = 100 × (0.75 × completeness + 0.25 × uniqueness), clamped to 0..100. IQR outliers are outside [Q1 - 1.5 IQR, Q3 + 1.5 IQR].
**Limits:** MVP profiles only and does not preserve raw files. Anomaly counts are descriptive, not causal diagnoses.
