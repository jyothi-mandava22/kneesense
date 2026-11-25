package com.kneesense.api.assessment.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record AssessmentSummaryResponse(
    Long resultId,
    int klGrade,
    BigDecimal confidence,
    String source,
    LocalDateTime createdAt
) {
}
