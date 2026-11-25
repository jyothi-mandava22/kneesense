package com.kneesense.api.assessment.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Patient-owned detail response. Clinician text is never serialized here. */
public record AssessmentDetailResponse(
    Long resultId,
    int klGrade,
    BigDecimal confidence,
    String source,
    LocalDateTime createdAt,
    String patientReport
) {
}
