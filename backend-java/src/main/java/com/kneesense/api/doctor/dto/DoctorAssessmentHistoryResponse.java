package com.kneesense.api.doctor.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record DoctorAssessmentHistoryResponse(
    Long resultId,
    int klGrade,
    BigDecimal confidence,
    String source,
    LocalDateTime createdAt
) {
}
